import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, realpathSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const namespace = 'org.example.evidence-bytes-node';
const ids = [`${namespace}.nonempty`, `${namespace}.calibrated-error`];
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const decoder = new TextDecoder('utf-8', { fatal: true });
const parse = (bytes) => JSON.parse(decoder.decode(bytes), (_key, value, context) => {
  if (typeof value === 'number' && /^-?(?:0|[1-9][0-9]*)$/.test(context.source)) {
    return BigInt(context.source);
  }
  return value;
});
const encode = (value) => JSON.stringify(value, (_key, item) =>
  typeof item === 'bigint' ? JSON.rawJSON(item.toString()) : item);

function captured(request, reference) {
  const matches = request.locations.filter((entry) => entry.sha256 === reference.sha256);
  if (matches.length !== 1) throw new Error('captured digest has no unique location');
  const path = matches[0].path;
  if (typeof path !== 'string' || path.startsWith('/') || path.includes('\\') ||
      path.split('/').some((part) => !part || part === '.' || part === '..')) {
    throw new Error('invalid relative input location');
  }
  if (typeof reference.size_bytes !== 'bigint' || reference.size_bytes < 0n ||
      reference.size_bytes > 1048576n) throw new Error('captured input exceeds method limit');
  const source = join(inputRoot, path);
  const stat = lstatSync(source);
  if (!stat.isFile() || realpathSync(source) !== source ||
      BigInt(stat.size) !== reference.size_bytes) {
    throw new Error('captured input is not the expected regular file');
  }
  const bytes = readFileSync(source);
  if (BigInt(bytes.length) !== reference.size_bytes || digest(bytes) !== reference.sha256) {
    throw new Error('captured input does not match its original identity');
  }
  return bytes;
}

const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== '--request' || !args[1]) {
  throw new Error('usage: node evaluate.mjs --request <path>');
}
const requestPath = resolve(args[1]);
const inputRoot = dirname(requestPath);
const requestStat = lstatSync(requestPath);
if (!requestStat.isFile() || realpathSync(requestPath) !== requestPath ||
    requestStat.size > 1048576) {
  throw new Error('request must be a bounded regular file without symlinks');
}
const requestBytes = readFileSync(requestPath);
if (requestBytes.length > 1048576) throw new Error('request exceeds method limit');
const request = parse(requestBytes);
if (request.schema_version !== 'evaluator-request.v1' || request.namespace !== namespace ||
    request.method.implementation !== namespace || request.method.version !== '1' ||
    request.expected_assertion_ids.length !== ids.length ||
    !ids.every((id) => request.expected_assertion_ids.includes(id))) {
  throw new Error('unexpected evaluator profile');
}
const sources = request.evidence.filter((entry) =>
  entry.artifact_id === 'method-input' && entry.media_type === 'application/json');
if (sources.length !== 1) throw new Error('one method-input JSON artifact required');
const source = sources[0];
const raw = captured(request, source);
const controls = parse(captured(request, request.controls));
const base = { source: 'product', namespace };
const results = [{
  ...base, assertion_id: ids[0], status: raw.length ? 'passed' : 'failed',
  observed_value: BigInt(raw.length), unit: 'B', evidence_sha256: [source.sha256],
}];
const calibration = controls.calibration;
if (calibration.state === 'unobserved') {
  results.push({
    ...base, assertion_id: ids[1], status: 'skipped', observed_value: null, unit: '1',
    message: 'this method has no observed offset calibration', evidence_sha256: [source.sha256],
  });
} else if (calibration.state === 'selected' && calibration.artifacts.length === 1) {
  const offsetRef = calibration.artifacts[0];
  const offsetBytes = captured(request, offsetRef);
  const evidence = [...new Set([source.sha256, offsetRef.sha256])];
  let counter, offset;
  try {
    counter = parse(raw)?.counter;
    offset = parse(offsetBytes)?.offset;
  } catch (error) {
    if (!(error instanceof SyntaxError) && !(error instanceof TypeError)) throw error;
  }
  if (typeof counter !== 'bigint' || typeof offset !== 'bigint') {
    results.push({
      ...base, assertion_id: ids[1], status: 'error', observed_value: null, unit: '1',
      message: 'counter and offset must be JSON integers', evidence_sha256: evidence,
    });
  } else {
    const difference = counter - offset;
    results.push({
      ...base, assertion_id: ids[1], status: difference === 0n ? 'passed' : 'failed',
      observed_value: difference, unit: '1', evidence_sha256: evidence,
    });
  }
} else {
  throw new Error('selected or unobserved calibration required');
}
process.stdout.write(encode({
  schema_version: 'evaluator-response.v1',
  request_sha256: digest(requestBytes),
  assertion_results: results,
}));
