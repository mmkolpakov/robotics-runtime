import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, chmod, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomUUID, createHash } from 'node:crypto';
import { Context } from 'cordis';
import { Admission } from '../src/plugins/admission/index.js';
import type { TrustedProfile } from '../src/plugins/admission/index.js';
import { RunOwner, RunStartupError } from '../src/plugins/run-owner/index.js';
import type { OwnedRun } from '../src/plugins/run-owner/index.js';
import { referenceFile } from '../src/plugins/application-lifecycle/index.js';
import type { CompletionHooks } from '../src/plugins/application-lifecycle/index.js';

export async function fixture(mode: 'good' | 'pending' | 'missing' | 'not-ready' | 'bad-cleanup' | 'logged-cleanup' | 'probe-error' | 'probe-timeout' = 'good') {
  const directory = await mkdtemp(join(tmpdir(), 'rr-owned-'));
  const runId = randomUUID();
  const modulePath = join(directory, 'provider.mjs');
  const profilePath = join(directory, 'cordis.yml');
  const resourcePath = join(directory, 'resource');
  const readyPath = join(directory, 'ready.json');
  const cleanupPath = join(directory, 'cleanup.json');
  const module = `import {writeFile,readFile,rm,access} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
async function ref(path){const raw=await readFile(path); return {uri:pathToFileURL(path).href,sha256:createHash('sha256').update(raw).digest('hex'),size_bytes:raw.length};}
async function exists(path){try{await access(path);return true;}catch{return false;}}
async function provider(ctx,config) {
 await writeFile(config.resourcePath,'owned finite resource');
 ctx.runResources.track({id:'file',ownerId:config.ownerId,
  cleanup:async()=>{ if(config.mode==='bad-cleanup')throw new Error('deliberate resource cleanup failure'); await rm(config.resourcePath);},
  verifyCleanup:async(signal)=>{signal.throwIfAborted(); const released=!(await exists(config.resourcePath)); await writeFile(config.cleanupPath,JSON.stringify({released,ownerId:config.ownerId})); return {released,evidenceRefs:[await ref(config.cleanupPath)]};}
 });
 if(config.mode==='logged-cleanup')ctx.effect(()=>async()=>{throw new Error('native caught cleanup failure');});
 ctx.provide('backend',{ready:async(signal)=>{signal.throwIfAborted(); if(config.mode==='probe-error')throw new Error('native readiness probe failed'); if(config.mode==='probe-timeout')return await new Promise(()=>{}); const present=await exists(config.resourcePath); await writeFile(config.readyPath,JSON.stringify({present,native_seconds:0.001,representation:'float64'})); return {ready:present&&config.mode!=='not-ready',evidenceRefs:[await ref(config.readyPath)]};}});
}
provider.inject=${JSON.stringify(mode==='pending'?['runResources','absentBackend']:['runResources'])};
export default provider;
`;
  await writeFile(modulePath, module);
  const config = { ownerId: runId, resourcePath, readyPath, cleanupPath, mode };
  const profile = `- id: backend\n  name: ${JSON.stringify(mode === 'missing' ? './missing.mjs' : './provider.mjs')}\n  config: ${JSON.stringify(config)}\n`;
  await writeFile(profilePath, profile);
  await chmod(modulePath, 0o444); await chmod(profilePath, 0o444);
  const files = await Promise.all([profilePath, modulePath].map(async path => ({ path, sha256: createHash('sha256').update(await readFile(path)).digest('hex') })));
  const descriptor: TrustedProfile = { id: runId, profilePath, files, requiredBindings: [{ entryId: 'backend', service: 'backend' }], isolatedServices: ['backend'], deadlineMs: mode === 'probe-timeout' ? 80 : 1000 };
  return { directory, runId, descriptor, resourcePath, readyPath, cleanupPath, profilePath };
}
export async function host(profiles: readonly TrustedProfile[]) {
  const ctx = new Context(); await ctx.plugin(Admission, { profiles }); await ctx.plugin(RunOwner); return ctx;
}
export function hooks(run: OwnedRun, directory: string, trace: string[]): CompletionHooks {
  const stage = (name: string) => async () => {
    trace.push(name); const path = join(directory, name + '.json');
    await writeFile(path, JSON.stringify({ runId: run.runId, stage: name }));
    return [await referenceFile(path)];
  };
  return { closeMeasurement: stage('close'), captureLastState: stage('capture'), drainRecorders: stage('drain'),
    exportEvidence: async () => { trace.push('export'); const path = join(directory, 'retained-resource.bin'); await writeFile(path, await readFile(join(directory, 'resource'))); return [await referenceFile(path)]; } };
}
