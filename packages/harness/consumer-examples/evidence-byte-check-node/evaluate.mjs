import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, writeFileSync } from 'node:fs';

const namespace = 'org.example.evidence-bytes-node';
const ids = [`${namespace}.nonempty`, `${namespace}.calibrated-error`];
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const parse = (bytes) => JSON.parse(bytes.toString('utf8'), (_key, value, context) => {
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
  const source = `/input/${path}`;
  const stat = lstatSync(source);
  if (!stat.isFile() || BigInt(stat.size) !== reference.size_bytes) {
    throw new Error('captured input is not the expected regular file');
  }
  const bytes = readFileSync(source);
  if (BigInt(bytes.length) !== reference.size_bytes || digest(bytes) !== reference.sha256) {
    throw new Error('captured input does not match its original identity');
  }
  return bytes;
}

const requestBytes = readFileSync('/input/request.json');
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
    if (!(error instanceof SyntaxError)) throw error;
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
writeFileSync('/output/response.json', encode({
  schema_version: 'evaluator-response.v1',
  request_sha256: digest(requestBytes),
  assertion_results: results,
}));
