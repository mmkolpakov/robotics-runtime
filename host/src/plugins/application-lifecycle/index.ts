import { readFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
export interface ArtifactRef { uri: string; sha256: string; size_bytes: number; }
export type RunPhase = 'preloading' | 'ready' | 'measuring' | 'closing-measurement' | 'capturing-last-state' |
  'draining-recorders' | 'exporting-evidence' | 'disposing' | 'verifying-cleanup' | 'completed' | 'retained' | 'error';
export interface PhaseObservation { phase: RunPhase; status: 'passed' | 'error'; diagnostic?: string; }
export interface CompletionHooks {
  closeMeasurement(signal: AbortSignal): Promise<readonly ArtifactRef[]>;
  captureLastState(signal: AbortSignal): Promise<readonly ArtifactRef[]>;
  drainRecorders(signal: AbortSignal): Promise<readonly ArtifactRef[]>;
  exportEvidence(signal: AbortSignal): Promise<readonly ArtifactRef[]>;
}
export async function referenceFile(path: string): Promise<ArtifactRef> {
  const file = resolve(path);
  const raw = await readFile(file);
  const facts = await stat(file);
  if (!facts.isFile() || facts.size !== raw.length) throw new Error('evidence file changed during capture');
  return { uri: pathToFileURL(file).href, sha256: createHash('sha256').update(raw).digest('hex'), size_bytes: raw.length };
}
export function lifecycleDeadline(value: number | undefined): number {
  const deadlineMs = value ?? 30000;
  if (!Number.isSafeInteger(deadlineMs) || deadlineMs <= 0 || deadlineMs > 2147483647) throw new RangeError('invalid lifecycle deadline');
  return deadlineMs;
}
export async function within<T>(work: (signal: AbortSignal) => Promise<T>, deadlineMs: number, cancel?: AbortSignal): Promise<T> {
  lifecycleDeadline(deadlineMs);
  const abort = new AbortController();
  const signal = cancel ? AbortSignal.any([abort.signal, cancel]) : abort.signal;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let listener: (() => void) | undefined;
  const interrupted = new Promise<never>((_, reject) => {
    listener = () => reject(signal.reason ?? new Error('lifecycle canceled'));
    signal.addEventListener('abort', listener, { once: true });
    if (signal.aborted) listener();
    timer = setTimeout(() => abort.abort(new Error('lifecycle deadline exceeded')), deadlineMs);
  });
  try { return await Promise.race([Promise.resolve().then(() => { signal.throwIfAborted(); return work(signal); }), interrupted]); }
  finally { if (timer) clearTimeout(timer); if (listener) signal.removeEventListener('abort', listener); }
}
