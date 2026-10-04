import { Service } from 'cordis';
import type { Context } from 'cordis';
import { readFile } from 'node:fs/promises';
import { requireWorkerCommand, workerRequest } from '../documents/index.js';
import type { WorkerCommand, WorkerLimits } from '../documents/index.js';
import type { JobResult } from '../jobs/index.js';
import { lifecycleDeadline, referenceFile } from '../application-lifecycle/index.js';
import type { ArtifactRef } from '../application-lifecycle/index.js';
export interface MediaConfig { command: WorkerCommand; producerPath: string; deadlineMs?: number; }
export interface MediaRequest extends WorkerLimits { configPath: string; reportPath: string; readyMarkerPath?: string; }
export interface MediaReport {
  status: 'eos' | 'error' | 'timeout' | 'canceled';
  gstreamer: string; playing: boolean;
  events: readonly { type: 'eos' | 'error'; message?: string; debug?: string }[];
  cleanup: { observed: string | null; succeeded: boolean };
  position?: { available: boolean; native_unit: string; native_representation: string; value: string | null };
}
export interface MediaResult { status: 'passed' | 'error' | 'incomplete'; job: JobResult; report?: MediaReport; reportRef?: ArtifactRef; diagnostic?: string; }
declare module 'cordis' { interface Context { mediaEndpoint: MediaEndpoint; } }
/** Invokes a finite GI worker; native pipeline owns all frame/transport/codec processing. */
export class MediaEndpoint extends Service {
  static inject = ['jobs'];
  readonly deadlineMs: number;
  readonly command: WorkerCommand;
  readonly producerPath: string;
  constructor(ctx: Context, config: MediaConfig) {
    const command = requireWorkerCommand(config?.command);
    const deadline = lifecycleDeadline(config?.deadlineMs);
    if (!config?.producerPath) throw new TypeError('configured GI worker path is required');
    super(ctx, 'mediaEndpoint');
    this.command = command; this.deadlineMs = deadline; this.producerPath = config.producerPath;
  }
  async capture(input: MediaRequest): Promise<MediaResult> {
    const job = await this.ctx.jobs.run(workerRequest(this.command, [this.producerPath, '--config', input.configPath,
      '--report', input.reportPath, '--deadline-ms', String(this.deadlineMs),
      ...(input.readyMarkerPath ? ['--ready-marker', input.readyMarkerPath] : [])], input));
    try {
      const report: MediaReport = JSON.parse(await readFile(input.reportPath, 'utf8'));
      const reportRef = await referenceFile(input.reportPath);
      const passed = job.ok && report.status === 'eos' && report.playing && report.events.some(event => event.type === 'eos')
        && report.cleanup.succeeded && report.cleanup.observed === 'null';
      return { status: passed ? 'passed' : 'error', job, report, reportRef };
    } catch (error) {
      return { status: 'incomplete', job, diagnostic: error instanceof Error ? error.message : String(error) };
    }
  }
}
export default MediaEndpoint;
