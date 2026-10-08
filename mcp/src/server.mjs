import { isAbsolute } from 'node:path';
import { Context, Jobs, Documents, Evaluation, isDisposed } from '@robotics-runtime/host';
import { McpServer, fromJsonSchema } from '@modelcontextprotocol/server';
import { createArtifactRegistry } from './artifacts.mjs';

const identifier = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/;
const object = (properties, required = []) => fromJsonSchema({
  type: 'object', properties, required, additionalProperties: false,
});
const id = { type: 'string', pattern: identifier.source };
const tools = [
  ['describe_contract', object({ schema_id: id }, ['schema_id']), 'Describe a registered public contract schema.'],
  ['validate_documents', object({ artifact_ids: { type: 'array', items: id, minItems: 1, maxItems: 16, uniqueItems: true } }, ['artifact_ids']), 'Validate registered immutable documents with the public contracts CLI.'],
  ['explain_bundle', object({ bundle_id: id }, ['bundle_id']), 'Explain a registered execution bundle without starting an observation.'],
  ['summarize_otlp', object({ artifact_id: id }, ['artifact_id']), 'Summarize a registered OTLP JSON-lines artifact.'],
  ['explain_result', object({ artifact_id: id }, ['artifact_id']), 'Explain a registered canonical result without evaluating it again.'],
  ['inspect_offline_readiness', object({}), 'Inspect installed offline dependencies; this is not native readiness.'],
];
const roles = ['scenario', 'runtime', 'model', 'dataset', 'permit', 'verification'];

function limits(input = {}) {
  const defaults = { timeoutMs: 30000, maxOutputBytes: 1048576, maxInputBytes: 16777216 };
  const ceilings = { timeoutMs: 120000, maxOutputBytes: 4194304, maxInputBytes: 67108864 };
  const result = { ...defaults, ...input };
  for (const [name, value] of Object.entries(result)) {
    if (!(name in defaults) || !Number.isSafeInteger(value) || value < 1 || value > ceilings[name]) throw new Error('invalid finite worker limit');
  }
  return result;
}
function command(value) {
  if (typeof value !== 'string' || !isAbsolute(value)) throw new Error('public CLI executable must be absolute');
  return { executable: value, extendEnv: false, env: { PATH: '/usr/bin:/bin', LANG: 'C.UTF-8', PYTHONDONTWRITEBYTECODE: '1' } };
}
function catalog(rows, make) {
  if (!Array.isArray(rows) || rows.length > 64) throw new Error('invalid trusted catalog');
  const result = new Map();
  for (const row of rows) {
    if (!identifier.test(row.id) || result.has(row.id)) throw new Error('invalid or duplicate catalog ID');
    result.set(row.id, make(row));
  }
  return result;
}
const response = value => ({ content: [{ type: 'text', text: JSON.stringify(value) }], isError: !value.ok });

export async function createOfflineAdapter(input) {
  if (typeof input.artifactRoot !== 'string' || !isAbsolute(input.artifactRoot)
    || typeof input.scratchRoot !== 'string' || !isAbsolute(input.scratchRoot)) throw new Error('absolute trusted roots required');
  const config = { ...input, limits: limits(input.limits) };
  const registry = await createArtifactRegistry(config);
  const schemas = catalog(config.schemas, row => {
    if (typeof row.schema !== 'string' || !/^[a-z][a-z0-9.-]{0,63}$/.test(row.schema)) throw new Error('invalid public schema name');
    return row.schema;
  });
  const bundles = catalog(config.bundles, row => {
    if (!row.scenario || !row.runtime || Object.keys(row).some(key => key !== 'id' && !roles.includes(key))) throw new Error('invalid registered bundle');
    for (const role of roles) if (row[role] !== undefined && !registry.has(row[role])) throw new Error('bundle artifact is not registered');
    return Object.freeze({ ...row });
  });
  const extensionSchemas = config.extensionSchemas ?? [];
  if (!Array.isArray(extensionSchemas) || extensionSchemas.length > 16) throw new Error('invalid trusted extension registry');
  const seenUris = new Set();
  for (const row of extensionSchemas) {
    if (typeof row.uri !== 'string' || !row.uri || row.uri.length > 512 || /[\s=\0]/.test(row.uri)
      || seenUris.has(row.uri) || !registry.has(row.artifact_id)) throw new Error('invalid or unregistered extension schema');
    seenUris.add(row.uri);
  }
  const contracts = command(config.contractsCli), harness = command(config.harnessCli);
  const owner = new Context();
  let ctx;
  const scope = owner.plugin(async child => {
    ctx = child;
    await child.plugin(Jobs, { timeoutMs: config.limits.timeoutMs, maxBufferBytes: config.limits.maxOutputBytes, killTimeoutMs: 2000 }).await();
    await child.plugin(Documents, contracts).await();
    await child.plugin(Evaluation, harness).await();
  });
  await scope.await();
  let closed = false, closing;
  let active = 0;
  async function call(name, args, signal) {
    if (closed) return response({ ok: false, error: 'offline adapter is closed', worker_started: false });
    if (active >= 4) return response({ ok: false, error: 'offline tool concurrency limit reached', worker_started: false });
    active++;
    let snapshot, outcome, workerStarted = false;
    try {
      let argv, ids = [], service = ctx.get('evaluation');
      if (name === 'describe_contract') {
        const schema = schemas.get(args.schema_id);
        if (!schema) throw new Error('schema ID is not registered');
        argv = ['describe', schema]; service = ctx.get('documents');
      } else if (name === 'validate_documents') {
        ids = [...new Set([...args.artifact_ids, ...extensionSchemas.map(row => row.artifact_id)])]; service = ctx.get('documents');
      } else if (name === 'explain_bundle') {
        const bundle = bundles.get(args.bundle_id);
        if (!bundle) throw new Error('bundle ID is not registered');
        ids = [...new Set([...roles.flatMap(role => bundle[role] === undefined ? [] : [bundle[role]]), ...extensionSchemas.map(row => row.artifact_id)])];
        argv = ['explain'];
        snapshot = await registry.snapshot(ids, signal);
        for (const role of roles) if (bundle[role] !== undefined) argv.push('--' + role, snapshot.files.get(bundle[role]));
        for (const row of extensionSchemas) argv.push('--extension-schema', row.uri + '=' + snapshot.files.get(row.artifact_id));
      } else if (name === 'summarize_otlp' || name === 'explain_result') {
        ids = [args.artifact_id];
      } else if (name === 'inspect_offline_readiness') argv = ['doctor', '--mode', 'offline', '--format', 'json'];
      else throw new Error('unsupported offline tool');
      snapshot ??= await registry.snapshot(ids, signal);
      const workerLimits = { timeoutMs: config.limits.timeoutMs, maxBufferBytes: config.limits.maxOutputBytes, cancelSignal: signal };
      let result;
      workerStarted = true;
      if (name === 'validate_documents') result = await service.validate(args.artifact_ids.map(value => snapshot.files.get(value)), { ...workerLimits,
        extensionSchemas: extensionSchemas.map(row => ({ uri: row.uri, path: snapshot.files.get(row.artifact_id) })) });
      else {
        if (name === 'summarize_otlp') argv = ['otel-summary', '--otel-metrics', snapshot.files.get(args.artifact_id), '--max-raw-evidence-bytes', String(config.limits.maxInputBytes)];
        if (name === 'explain_result') argv = ['why', '--format', 'json', snapshot.files.get(args.artifact_id)];
        result = await service.execute(argv, workerLimits);
      }
      outcome = { ...result, exitCode: result.exitCode ?? null, signal: result.signal ?? null, code: result.code ?? null,
        diagnostic: result.diagnostic ?? null, inputRefs: snapshot.references, scope: 'offline public CLI explanation; not qualification' };
    } catch (error) {
      outcome = { ok: false, worker_started: workerStarted, canceled: Boolean(signal?.aborted), timedOut: false, error: String(error.message ?? error) };
    } finally {
      try { await snapshot?.close(); }
      catch (error) { outcome = { ...outcome, ok: false, cleanupError: String(error.message ?? error) }; }
      active--;
    }
    return response(outcome);
  }
  return {
    serverFactory() {
      const server = new McpServer({ name: 'robotics-runtime-offline', version: '0.1.0-rc.0' }, { capabilities: { tools: {} } });
      for (const [name, inputSchema, description] of tools) {
        server.registerTool(name, { description, inputSchema,
          annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } },
        (args, context) => call(name, args, context.mcpReq.signal));
      }
      return server;
    },
    close() {
      closed = true;
      return closing ??= scope.dispose().then(() => {
        if (!isDisposed(scope)) throw new Error('offline service scope did not settle disposal');
      });
    },
  };
}
