import assert from 'node:assert/strict';
import {readFile, readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {basename, join} from 'node:path';
import {pathToFileURL} from 'node:url';

const packageName = '@robotics-runtime/host';
const hex = (value, length) => typeof value === 'string' && new RegExp('^[a-f0-9]{' + length + '}$').test(value);
export function makePlan(pkg, input) {
  assert.equal(pkg.name, packageName, 'only the core host package is admitted');
  assert.equal(pkg.private, true, 'host assets keep registry publication disabled');
  assert.ok(typeof pkg.version === 'string' && pkg.version && !/[\s/\\]/.test(pkg.version));
  const candidate = 'host-v' + pkg.version;
  assert.equal(input.candidate || candidate, candidate, 'candidate must equal the committed host version');
  assert.ok(['pull_request', 'push', 'workflow_dispatch', 'local'].includes(input.event));
  for (const key of ['source_revision', 'source_tree']) assert.ok(hex(input[key], 40), 'exact Git identity required');
  const reference = input.reference_revision ? {
    source_revision: input.reference_revision, source_tree: input.reference_tree,
    asset_sha256: input.reference_asset_sha256,
  } : null;
  if (reference) {
    assert.ok(hex(reference.source_revision, 40) && hex(reference.source_tree, 40) && hex(reference.asset_sha256, 64),
      'reference source, tree and asset SHA must be explicit together');
  } else assert.ok(!input.reference_tree && !input.reference_asset_sha256, 'incomplete reference binding');
  return {candidate, name: pkg.name, version: pkg.version, source_revision: input.source_revision,
    source_tree: input.source_tree, toolchain: {node: pkg.engines.node, npm: pkg.engines.npm},
    reference, scope: 'package integrity; native acceptance is established separately'};
}
export function requirePublicationCommit(source, trigger, live) {
  assert.ok([source, trigger, live].every(value => hex(value, 40)), 'exact publication commit required');
  assert.equal(source, trigger, 'manifest source differs from the tag-trigger commit');
  assert.equal(live, source, 'live remote tag moved from the built commit');
}
export async function verifyArtifact(pkg, plan, rows, directory) {
  makePlan(pkg, {...plan, event: 'local', reference_revision: plan.reference?.source_revision,
    reference_tree: plan.reference?.source_tree, reference_asset_sha256: plan.reference?.asset_sha256});
  assert.equal(rows.length, 1, 'exactly one npm-pack result is required');
  const row = rows[0], filename = 'robotics-runtime-host-' + pkg.version + '.tgz';
  assert.equal(plan.candidate, 'host-v' + pkg.version);
  assert.equal(row.name, packageName); assert.equal(row.version, pkg.version);
  assert.equal(row.filename, filename, 'only the expected npm archive is admitted');
  assert.equal(basename(row.filename), row.filename, 'asset cannot escape its directory');
  assert.deepEqual((await readdir(directory)).sort(), [filename], 'unexpected release asset');
  const inventory = new Set(row.files.map(file => file.path));
  assert.ok(inventory.has('package.json'), 'package metadata is missing');
  for (const entry of Object.values(pkg.exports)) for (const key of ['import', 'types']) {
    assert.ok(typeof entry[key] === 'string' && entry[key].startsWith('./'));
    assert.ok(inventory.has(entry[key].slice(2)), 'declared ' + key + ' export is missing: ' + entry[key]);
  }
  for (const prefix of ['schemas/', 'producers/', 'proto/'])
    assert.ok([...inventory].some(path => path.startsWith(prefix)), 'required resource closure is missing: ' + prefix);
  for (const path of ['tools/fetch-mavsdk-server.mjs', 'tools/mavsdk-server.v4.0.3.json'])
    assert.ok(inventory.has(path), 'required installer metadata is missing: ' + path);
  const raw = await readFile(join(directory, filename));
  assert.equal('sha512-' + createHash('sha512').update(raw).digest('base64'), row.integrity, 'npm integrity differs');
  const sha256 = createHash('sha256').update(raw).digest('hex'), reference = plan.reference;
  const reference_matches = Boolean(reference && reference.source_tree === plan.source_tree && reference.asset_sha256 === sha256);
  return {...plan, filename, sha256, npm_pack: row, reference_matches};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [command, ...args] = process.argv.slice(2);
  const json = async path => JSON.parse(await readFile(path, 'utf8'));
  const pkg = await json('package.json');
  let result;
  if (command === 'plan') {
    const [candidate, event, source_revision, source_tree, reference_revision = '', reference_tree = '', reference_asset_sha256 = ''] = args;
    result = makePlan(pkg, {candidate, event, source_revision, source_tree, reference_revision, reference_tree, reference_asset_sha256});
  } else if (command === 'tag') {
    assert.equal(args.length, 2);
    const manifest = await json(args[0]);
    requirePublicationCommit(manifest.source_revision, process.env.GITHUB_SHA, args[1]);
    result = {source_revision: manifest.source_revision, live_commit: args[1]};
  } else {
    assert.equal(command, 'verify'); assert.equal(args.length, 3);
    result = await verifyArtifact(pkg, await json(args[0]), await json(args[1]), args[2]);
  }
  Object.assign(result, {repository: process.env.GITHUB_REPOSITORY || null, source_ref: process.env.GITHUB_REF || null,
    source_date_epoch: process.env.SOURCE_DATE_EPOCH || null});
  result.package_lock_sha256 = createHash('sha256').update(await readFile('package-lock.json')).digest('hex');
  if (command === 'verify') result.toolchain.typescript = (await json('node_modules/typescript/package.json')).version;
  console.log(JSON.stringify(result, null, 2));
}
