import { Context, Service, FiberState } from 'cordis';
import type { Fiber, Message } from 'cordis';
import Loader from '@cordisjs/plugin-loader';
import { dirname } from 'node:path';
import { pathToFileURL } from 'node:url';
import { randomUUID } from 'node:crypto';
import { within } from '../application-lifecycle/index.js';
import type { ArtifactRef, CompletionHooks, PhaseObservation, RunPhase } from '../application-lifecycle/index.js';
import type { AdmittedProfile } from '../admission/index.js';

export interface CleanupObservation { released: boolean; evidenceRefs: readonly ArtifactRef[]; diagnostic?: string; }
export interface OwnedResource {
  id: string; ownerId: string;
  cleanup(): Promise<void>; verifyCleanup(signal: AbortSignal): Promise<CleanupObservation>;
}
export interface ResourceOutcome extends CleanupObservation { id: string; ownerId: string; attempted: boolean; cleanupError?: string; }
interface ResourceRecord { resource: OwnedResource; attempted: boolean; cleanupError?: string; }
export interface BackendReadiness { ready: boolean; evidenceRefs: readonly ArtifactRef[]; }
export interface BackendProbe { ready(signal: AbortSignal): Promise<BackendReadiness>; }
export interface RunCompletion {
  runId: string; status: 'passed' | 'error' | 'incomplete'; phases: readonly PhaseObservation[];
  resourceOutcomes: readonly ResourceOutcome[]; evidenceRefs: readonly ArtifactRef[]; errors: readonly string[];
}
declare module 'cordis' { interface Context { runOwner: RunOwner; runResources: RunResources; } }
const reason = (error: unknown) => error instanceof Error ? error.message : String(error);

export class RunResources extends Service {
  private readonly records = new Map<string, ResourceRecord>();
  constructor(ctx: Context, readonly ownerId: string) { super(ctx, 'runResources'); }
  track(resource: OwnedResource): void {
    if (resource.ownerId !== this.ownerId) throw new Error('cannot acquire a foreign owner resource');
    if (this.records.has(resource.id)) throw new Error('resource is already owned');
    const record: ResourceRecord = { resource, attempted: false };
    this.records.set(resource.id, record);
    this.ctx.effect(() => async () => {
      record.attempted = true;
      try { await resource.cleanup(); }
      catch (error) { record.cleanupError = reason(error); throw error; }
    }, `resource:${resource.id}`);
  }
  pending(): ResourceOutcome[] {
    return [...this.records.values()].map(record => ({
      id: record.resource.id, ownerId: this.ownerId, attempted: record.attempted, released: false,
      evidenceRefs: [], diagnostic: 'destructive cleanup deferred until retained evidence export succeeds',
    }));
  }
  async verify(deadlineMs: number): Promise<ResourceOutcome[]> {
    return Promise.all([...this.records.values()].map(async record => {
      try {
        const observation = await within(signal => record.resource.verifyCleanup(signal), deadlineMs);
        return { ...observation, id: record.resource.id, ownerId: this.ownerId, attempted: record.attempted,
          ...(record.cleanupError === undefined ? {} : { cleanupError: record.cleanupError }) };
      } catch (error) {
        return { id: record.resource.id, ownerId: this.ownerId, attempted: record.attempted,
          released: false, evidenceRefs: [], diagnostic: reason(error),
          ...(record.cleanupError === undefined ? {} : { cleanupError: record.cleanupError }) };
      }
    }));
  }
}

function descends(fiber: Fiber | undefined, parent: Fiber | undefined): boolean {
  if (!fiber || !parent) return false;
  while (fiber !== fiber.parent.fiber) {
    if (fiber === parent || (parent.runtime && fiber.runtime?.callback === parent.runtime.callback)) return true;
    fiber = fiber.parent.fiber;
  }
  return fiber === parent || !!(parent.runtime && fiber.runtime?.callback === parent.runtime.callback);
}
export class OwnedRun {
  phase: RunPhase = 'preloading';
  readonly phases: PhaseObservation[] = [];
  readonly evidenceRefs: ArtifactRef[] = [];
  readonly errors: string[] = [];
  readonly capturedErrors: string[] = [];
  fiber!: Fiber;
  includeId!: string;
  resources!: RunResources;
  context!: Context;
  loader!: Loader;
  private completion: Promise<RunCompletion> | undefined;
  private readonly stopLogging: () => unknown;
  constructor(readonly owner: Context, readonly runId: string, readonly profile: AdmittedProfile, private readonly releaseOwner: () => void) {
    this.stopLogging = owner.logger.exporter({ export: (message: Message) => {
      if (message.type !== 'error' || !descends(message.fiber?.deref(), this.fiber)) return;
      if (this.capturedErrors.length < 1000) this.capturedErrors.push(message.args.map(reason).join(' '));
      else if (!this.errors.includes('Cordis error log overflow')) this.errors.push('Cordis error log overflow');
    } });
  }
  beginMeasurement(): void {
    if (this.phase !== 'ready') throw new Error('measurement requires admitted ready composition');
    this.phase = 'measuring'; this.phases.push({ phase: 'measuring', status: 'passed' });
  }
  finish(hooks?: CompletionHooks): Promise<RunCompletion> {
    return this.completion ??= this.complete(hooks);
  }
  retryExport(exportEvidence: CompletionHooks['exportEvidence']): Promise<RunCompletion> {
    if (this.phase !== 'retained') throw new Error('only retained runs can retry export');
    this.phase = 'exporting-evidence';
    return this.completion = this.exportAndCleanup(exportEvidence);
  }
  private retained(diagnostic: string): RunCompletion {
    this.phase = 'retained';
    this.phases.push({ phase: 'retained', status: 'error', diagnostic });
    return { runId: this.runId, status: 'incomplete', phases: [...this.phases],
      resourceOutcomes: this.resources?.pending() ?? [], evidenceRefs: [...this.evidenceRefs], errors: [...this.errors] };
  }
  private async complete(hooks?: CompletionHooks): Promise<RunCompletion> {
    const deadline = this.profile.deadlineMs ?? 30000;
    if (this.phase !== 'measuring') this.errors.push('measurement was not started');
    const stages = [
      ['closing-measurement', hooks?.closeMeasurement],
      ['capturing-last-state', hooks?.captureLastState],
      ['draining-recorders', hooks?.drainRecorders],
    ] as const;
    for (const [phase, work] of stages) {
      this.phase = phase;
      if (!work) {
        const diagnostic = `lifecycle stage has no evidence producer: ${phase}`;
        this.errors.push(diagnostic); this.phases.push({ phase, status: 'error', diagnostic }); continue;
      }
      try {
        this.evidenceRefs.push(...await within(signal => work(signal), deadline));
        this.phases.push({ phase, status: 'passed' });
      } catch (error) {
        const diagnostic = reason(error);
        this.errors.push(diagnostic); this.phases.push({ phase, status: 'error', diagnostic });
      }
    }
    return this.exportAndCleanup(hooks?.exportEvidence);
  }
  private async exportAndCleanup(exportEvidence?: CompletionHooks['exportEvidence']): Promise<RunCompletion> {
    const deadline = this.profile.deadlineMs ?? 30000;
    this.phase = 'exporting-evidence';
    try {
      if (!exportEvidence) throw new Error('evidence export producer is missing');
      const references = await within(signal => exportEvidence(signal), deadline);
      if (!references.length) throw new Error('evidence export returned no retained references');
      this.evidenceRefs.push(...references);
      this.phases.push({ phase: 'exporting-evidence', status: 'passed' });
    } catch (error) {
      const diagnostic = reason(error);
      this.errors.push(diagnostic); this.phases.push({ phase: 'exporting-evidence', status: 'error', diagnostic });
      return this.retained('evidence export failed; destructive cleanup is deferred');
    }
    let disposalComplete = false;
    this.phase = 'disposing';
    try { await within(() => this.fiber.dispose(), deadline); disposalComplete = this.fiber.state === FiberState.DISPOSED; if (!disposalComplete) throw new Error('Cordis dispose resolved without observed DISPOSED state'); this.phases.push({ phase: 'disposing', status: 'passed' }); }
    catch (error) { this.errors.push(reason(error)); this.phases.push({ phase: 'disposing', status: 'error', diagnostic: reason(error) }); }
    this.phase = 'verifying-cleanup';
    const resourceOutcomes = this.resources ? await this.resources.verify(deadline) : [];
    this.evidenceRefs.push(...resourceOutcomes.flatMap(outcome => outcome.evidenceRefs));
    const cleanupPassed = resourceOutcomes.every(outcome => outcome.attempted && outcome.released && outcome.evidenceRefs.length > 0 && !outcome.cleanupError);
    if (!cleanupPassed) this.errors.push('independent resource cleanup verification failed');
    this.errors.push(...resourceOutcomes.flatMap(outcome => outcome.cleanupError ? [outcome.cleanupError] : []));
    this.errors.push(...this.capturedErrors.map(message => `Cordis: ${message}`));
    this.phases.push({ phase: 'verifying-cleanup', status: cleanupPassed && !this.capturedErrors.length ? 'passed' : 'error' });
    await this.stopLogging();
    const status = this.errors.length ? 'error' : resourceOutcomes.length ? 'passed' : 'incomplete';
    this.phase = status === 'passed' ? 'completed' : 'error';
    this.phases.push({ phase: this.phase, status: status === 'passed' ? 'passed' : 'error' });
    if (disposalComplete && resourceOutcomes.every(outcome => outcome.attempted && outcome.released && outcome.evidenceRefs.length > 0)) this.releaseOwner();
    return { runId: this.runId, status, phases: [...this.phases], resourceOutcomes,
      evidenceRefs: [...this.evidenceRefs], errors: [...this.errors] };
  }
}
export class RunStartupError extends Error {
  constructor(message: string, readonly completion: RunCompletion, readonly run: OwnedRun) { super(message); this.name = 'RunStartupError'; }
}

/** Owns one isolated native Fiber tree. Backend operations remain provider-specific. */
export class RunOwner extends Service {
  static inject = ['admission'];
  private readonly active = new Set<string>();
  constructor(ctx: Context) { super(ctx, 'runOwner'); }
  async start(profileId: string, runId = randomUUID()): Promise<OwnedRun> {
    if (this.active.has(runId)) throw new Error('run ID is already owned');
    this.active.add(runId);
    let profile: AdmittedProfile;
    try {
      profile = await this.ctx.admission.admit(profileId);
      this.ctx.admission.assertIssued(profile);
    } catch (error) { this.active.delete(runId); throw error; }
    const run = new OwnedRun(this.ctx, runId, profile, () => this.active.delete(runId));
    let scope = this.ctx;
    for (const name of new Set(['loader', 'runResources', 'baseUrl', ...profile.isolatedServices, ...profile.requiredBindings.map(item => item.service)])) {
      scope = scope.isolate(name, Symbol(runId + ':' + name));
    }
    run.fiber = scope.plugin(async (ctx: Context) => {
      run.context = ctx;
      const baseUrl = pathToFileURL(dirname(profile.profilePath)).href + '/';
      ctx.provide('baseUrl', baseUrl);
      await ctx.plugin(RunResources, runId);
      const resources = ctx.get('runResources');
      if (!resources) throw new Error('run resource service is missing');
      run.resources = resources;
      await ctx.plugin(Loader, { baseUrl });
      const loader = ctx.get('loader');
      if (!loader) throw new Error('native loader binding is missing');
      run.loader = loader;
      run.includeId = await loader.create({ name: '@cordisjs/plugin-include', config: { path: profile.profilePath } });
      await loader.await();
    });
    try {
      await within(() => run.fiber.await(), profile.deadlineMs ?? 30000);
      if (run.fiber.state !== FiberState.ACTIVE) throw new Error('run Fiber is not ACTIVE');
      const include = run.loader.resolve(run.includeId);
      if (!include.fiber) throw new Error('Include import has no Fiber');
      await include.fiber.await();
      if (include.fiber.state !== FiberState.ACTIVE) throw new Error('Include Fiber is not ACTIVE');
      for (const binding of profile.requiredBindings) {
        const entry = run.loader.resolve(`${run.includeId}:${binding.entryId}`);
        if (!entry.fiber) throw new Error(`required module import has no Fiber: ${binding.entryId}`);
        await within(() => entry.fiber!.await(), profile.deadlineMs ?? 30000);
        if (entry.fiber.state !== FiberState.ACTIVE) throw new Error(`required Fiber is not ACTIVE: ${binding.entryId}`);
        const backend: unknown = run.context.get(binding.service);
        if (!backend || typeof (backend as BackendProbe).ready !== 'function') throw new Error(`required backend binding is missing: ${binding.service}`);
        const observed = await within(signal => (backend as BackendProbe).ready(signal), profile.deadlineMs ?? 30000);
        run.evidenceRefs.push(...observed.evidenceRefs);
        if (!observed.ready || !observed.evidenceRefs.length) throw new Error(`backend has no observed readiness: ${binding.service}`);
      }
      run.phase = 'ready'; run.phases.push({ phase: 'preloading', status: 'passed' }, { phase: 'ready', status: 'passed' });
      return run;
    } catch (error) {
      run.errors.push(reason(error)); run.phases.push({ phase: 'preloading', status: 'error', diagnostic: reason(error) });
      throw new RunStartupError(reason(error), await run.finish(), run);
    }
  }
}
export default RunOwner;
