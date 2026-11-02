import { Service } from 'cordis';
import type { Context } from 'cordis';
import { execa } from 'execa';
export interface JobRequest {
  executable: string; args: readonly string[]; cwd?: string; timeoutMs?: number;
  maxBufferBytes?: number; cancelSignal?: AbortSignal; env?: Readonly<Record<string, string>>; extendEnv?: boolean;
}
export interface JobResult {
  ok: boolean; exitCode: number | undefined; signal: string | undefined;
  timedOut: boolean; canceled: boolean; stdout: string; stderr: string;
  diagnostic: string | undefined; code: string | undefined; durationMs: number;
}
export interface BytesJobRequest extends JobRequest {
  stderrMaxBufferBytes?: number;
}
export interface BytesJobResult extends Omit<JobResult, 'stdout' | 'stderr'> {
  stdout: Uint8Array; stderr: Uint8Array; isMaxBuffer: boolean;
}
export interface JobsConfig { timeoutMs?: number; maxBufferBytes?: number; killTimeoutMs?: number; }
declare module 'cordis' { interface Context { jobs: Jobs; } }
function bound(value: number, ceiling: number, name: string): number {
  if (!Number.isSafeInteger(value) || value <= 0 || value > ceiling) throw new RangeError(`${name} must be a positive integer <= ${ceiling}`);
  return value;
}
/** Owns finite subprocesses; worker policy belongs to admitted profiles. */
export class Jobs extends Service {
  readonly timeoutMs: number; readonly maxBufferBytes: number; readonly killTimeoutMs: number;
  private readonly abort = new AbortController();
  private readonly running = new Set<Promise<JobResult | BytesJobResult>>();
  constructor(ctx: Context, config: JobsConfig = {}) {
    super(ctx, 'jobs');
    this.timeoutMs = bound(config.timeoutMs ?? 30000, 2147483647, 'timeoutMs');
    this.maxBufferBytes = bound(config.maxBufferBytes ?? 1048576, 2147483647, 'maxBufferBytes');
    this.killTimeoutMs = bound(config.killTimeoutMs ?? 2000, 30000, 'killTimeoutMs');
  }
  async *[Service.init]() {
    yield async () => { this.abort.abort(new Error('jobs owner disposed')); await Promise.allSettled(this.running); };
  }
  run(request: JobRequest): Promise<JobResult> {
    return this.execute(request, false);
  }
  runBytes(request: BytesJobRequest): Promise<BytesJobResult> {
    return this.execute(request, true);
  }
  private execute(request: JobRequest, bytes: false): Promise<JobResult>;
  private execute(request: BytesJobRequest, bytes: true): Promise<BytesJobResult>;
  private execute(request: BytesJobRequest, bytes: boolean): Promise<JobResult | BytesJobResult> {
    const timeout = bound(request.timeoutMs ?? this.timeoutMs, this.timeoutMs, 'timeoutMs');
    const maxBuffer = bound(request.maxBufferBytes ?? this.maxBufferBytes, this.maxBufferBytes, 'maxBufferBytes');
    if (!request.executable || request.args.some(value => typeof value !== 'string')) throw new TypeError('executable and argv must be strings');
    const capture = bytes ? {
      encoding: 'buffer' as const, stripFinalNewline: false, lines: false, buffer: true,
      all: false, verbose: 'none' as const, stdin: 'ignore' as const,
      stdout: 'pipe' as const, stderr: 'pipe' as const,
      maxBuffer: {
        stdout: maxBuffer,
        stderr: bound(request.stderrMaxBufferBytes ?? Math.min(this.maxBufferBytes, 65536), this.maxBufferBytes, 'stderrMaxBufferBytes'),
      },
    } : { encoding: 'utf8' as const, maxBuffer };
    const cancelSignal = request.cancelSignal ? AbortSignal.any([this.abort.signal, request.cancelSignal]) : this.abort.signal;
    const started = performance.now();
    const task = (async (): Promise<JobResult | BytesJobResult> => {
      const result = await execa(request.executable, [...request.args], {
        ...(request.cwd === undefined ? {} : { cwd: request.cwd }),
        env: { ...(request.env ?? {}) },
        extendEnv: request.extendEnv ?? false, killDescendants: true,
        timeout, cancelSignal, reject: false, shell: false,
        ...capture, forceKillAfterDelay: this.killTimeoutMs,
      });
      const status = { ok: !result.failed, exitCode: result.exitCode, signal: result.signal,
        timedOut: result.timedOut, canceled: result.isCanceled,
        diagnostic: result.failed ? result.shortMessage : undefined, code: result.code, durationMs: performance.now() - started };
      if (bytes) {
        if (!(result.stdout instanceof Uint8Array) || !(result.stderr instanceof Uint8Array)) throw new TypeError('Execa did not return byte streams');
        return { ...status, stdout: result.stdout, stderr: result.stderr, isMaxBuffer: result.isMaxBuffer };
      }
      if (typeof result.stdout !== 'string' || typeof result.stderr !== 'string') throw new TypeError('Execa did not return text streams');
      return { ...status, stdout: result.stdout, stderr: result.stderr };
    })();
    this.running.add(task);
    void task.finally(() => this.running.delete(task)).catch(() => {});
    return task;
  }
}
export default Jobs;
