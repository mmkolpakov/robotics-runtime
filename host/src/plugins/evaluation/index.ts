import { Service } from 'cordis';
import type { Context } from 'cordis';
import { extensionArguments, requireWorkerCommand, workerRequest } from '../documents/index.js';
import type { ExtensionSchema, WorkerCommand, WorkerLimits } from '../documents/index.js';
import type { JobResult } from '../jobs/index.js';
declare module 'cordis' { interface Context { evaluation: Evaluation; } }
export interface OfflineEvaluation extends WorkerLimits {
  scenario: string; runtime: string; runId: string; domainId: string; runContext: string; evidenceIndex: string;
  otelMetrics: string; windowStartNs: string | bigint; windowEndNs: string | bigint;
  outputDirectory: string; diagnosticOutput: string; extensionSchemas?: readonly ExtensionSchema[]; maxRawEvidenceBytes?: number;
}
function integerNs(value: string | bigint): string {
  const raw = String(value);
  if (!/^(0|[1-9][0-9]*)$/.test(raw)) throw new TypeError('nanoseconds must be an unsigned decimal string or bigint');
  return raw;
}
/** Delegates evaluation and JSON/JUnit/diagnostics to the installed public harness. */
export class Evaluation extends Service {
  static inject = ['jobs'];
  readonly command: WorkerCommand;
  constructor(ctx: Context, command: WorkerCommand) {
    const configured = requireWorkerCommand(command);
    super(ctx, 'evaluation');
    this.command = configured;
  }
  execute(args: readonly string[], limits: WorkerLimits = {}): Promise<JobResult> {
    return this.ctx.jobs.run(workerRequest(this.command, args, limits));
  }
  evaluate(input: OfflineEvaluation): Promise<JobResult> {
    const args = ['evaluate', '--scenario', input.scenario, '--runtime', input.runtime, '--run-id', input.runId,
      '--domain-id', input.domainId, '--run-context', input.runContext, '--evidence-index', input.evidenceIndex,
      '--otel-metrics', input.otelMetrics, '--window-start-ns', integerNs(input.windowStartNs),
      '--window-end-ns', integerNs(input.windowEndNs), '--output', input.outputDirectory,
      '--diagnostic-output', input.diagnosticOutput, ...extensionArguments(input.extensionSchemas)];
    if (input.maxRawEvidenceBytes !== undefined) args.push('--max-raw-evidence-bytes', String(input.maxRawEvidenceBytes));
    return this.execute(args, input);
  }
}
export default Evaluation;
