import { open, stat } from 'node:fs/promises';
import { constants, type BigIntStats } from 'node:fs';
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
export interface FileReferenceOptions { maxBytes?: number; }
function unchanged(before: BigIntStats, after: BigIntStats): boolean {
  return after.isFile() && before.dev === after.dev && before.ino === after.ino &&
    before.size === after.size && before.mtimeNs === after.mtimeNs && before.ctimeNs === after.ctimeNs;
}
/** Capture a byte reference; providers still qualify the retained evidence themselves. */
export async function referenceFile(path: string, options: FileReferenceOptions = {}): Promise<ArtifactRef> {
  const maxBytes = options.maxBytes;
  if (maxBytes !== undefined && (!Number.isSafeInteger(maxBytes) || maxBytes < 0)) {
    throw new RangeError('maxBytes must be a nonnegative safe integer');
  }
  const file = resolve(path);
  const before = await stat(file, { bigint: true });
  if (!before.isFile()) throw new Error('evidence must be a regular file');
  if (before.size > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('evidence size exceeds the safe integer range');
  if (maxBytes !== undefined && before.size > BigInt(maxBytes)) throw new Error('evidence exceeds maxBytes');
  // Follow existing file aliases; NONBLOCK prevents a replaced FIFO from blocking open.
  const handle = await open(file, constants.O_RDONLY | constants.O_NONBLOCK);
  try {
    if (!unchanged(before, await handle.stat({ bigint: true }))) throw new Error('evidence file changed during capture');
    const hash = createHash('sha256');
    let size = 0;
    // One extra byte detects growth without following an indefinitely growing file.
    const stream = handle.createReadStream({ autoClose: false, end: Number(before.size), highWaterMark: 64 * 1024 });
    for await (const block of stream) {
      size += block.length;
      if (maxBytes !== undefined && size > maxBytes) throw new Error('evidence exceeds maxBytes');
      if (BigInt(size) > before.size) throw new Error('evidence file changed during capture');
      hash.update(block);
    }
    const after = await handle.stat({ bigint: true });
    const current = await stat(file, { bigint: true }).catch(error => {
      throw new Error('evidence file changed during capture', { cause: error });
    });
    if (BigInt(size) !== before.size || !unchanged(before, after) || !unchanged(before, current)) {
      throw new Error('evidence file changed during capture');
    }
    return { uri: pathToFileURL(file).href, sha256: hash.digest('hex'), size_bytes: size };
  } finally { await handle.close(); }
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
