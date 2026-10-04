import { Service } from 'cordis';
import type { Context } from 'cordis';
import type { JobRequest, JobResult } from '../jobs/index.js';
export interface WorkerCommand { executable: string; prefixArgs?: readonly string[]; cwd?: string; env?: Readonly<Record<string, string>>; }
export interface ExtensionSchema { uri: string; path: string; }
export type WorkerLimits = Pick<JobRequest, 'timeoutMs' | 'maxBufferBytes' | 'cancelSignal'>;
export function extensionArguments(schemas: readonly ExtensionSchema[] = []): string[] {
  return schemas.flatMap(schema => ['--extension-schema', `${schema.uri}=${schema.path}`]);
}
export function workerRequest(command: WorkerCommand, args: readonly string[], limits: WorkerLimits): JobRequest {
  return { executable: command.executable, args: [...(command.prefixArgs ?? []), ...args],
    ...(limits.timeoutMs === undefined ? {} : { timeoutMs: limits.timeoutMs }),
    ...(limits.maxBufferBytes === undefined ? {} : { maxBufferBytes: limits.maxBufferBytes }),
    ...(limits.cancelSignal === undefined ? {} : { cancelSignal: limits.cancelSignal }),
    ...(command.cwd === undefined ? {} : { cwd: command.cwd }), ...(command.env === undefined ? {} : { env: command.env }) };
}
declare module 'cordis' { interface Context { documents: Documents; } }
/** Python owns parsing, subject rules and exact writer. */
export class Documents extends Service {
  static inject = ['jobs'];
  constructor(ctx: Context, readonly command: WorkerCommand = { executable: 'robotics-contracts' }) { super(ctx, 'documents'); }
  validate(paths: readonly string[], options: WorkerLimits & { schema?: string; extensionSchemas?: readonly ExtensionSchema[] } = {}): Promise<JobResult> {
    return this.ctx.jobs.run(workerRequest(this.command, ['--format', 'json', 'validate', ...paths,
      ...(options.schema ? ['--schema', options.schema] : []), ...extensionArguments(options.extensionSchemas)], options));
  }
  execute(args: readonly string[], limits: WorkerLimits = {}): Promise<JobResult> {
    return this.ctx.jobs.run(workerRequest(this.command, ['--format', 'json', ...args], limits));
  }
}
export default Documents;
