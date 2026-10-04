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
  private readonly running = new Set<Promise<JobResult>>();
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
    const timeout = bound(request.timeoutMs ?? this.timeoutMs, this.timeoutMs, 'timeoutMs');
    const maxBuffer = bound(request.maxBufferBytes ?? this.maxBufferBytes, this.maxBufferBytes, 'maxBufferBytes');
    if (!request.executable || request.args.some(value => typeof value !== 'string')) throw new TypeError('executable and argv must be strings');
    const cancelSignal = request.cancelSignal ? AbortSignal.any([this.abort.signal, request.cancelSignal]) : this.abort.signal;
    const started = performance.now();
    const task = (async (): Promise<JobResult> => {
      const result = await execa(request.executable, [...request.args], {
        ...(request.cwd === undefined ? {} : { cwd: request.cwd }),
        ...(request.env === undefined ? {} : { env: { ...request.env } }),
        ...(request.extendEnv === undefined ? {} : { extendEnv: request.extendEnv }),
        timeout, maxBuffer, cancelSignal, reject: false, shell: false,
        encoding: 'utf8', forceKillAfterDelay: this.killTimeoutMs,
      });
      return { ok: !result.failed, exitCode: result.exitCode, signal: result.signal,
        timedOut: result.timedOut, canceled: result.isCanceled, stdout: result.stdout, stderr: result.stderr,
        diagnostic: result.failed ? result.shortMessage : undefined, code: result.code, durationMs: performance.now() - started };
    })();
    this.running.add(task);
    void task.finally(() => this.running.delete(task)).catch(() => {});
    return task;
  }
}
export default Jobs;
