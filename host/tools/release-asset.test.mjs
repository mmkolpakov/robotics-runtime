import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtemp, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {makePlan, verifyArtifact} from './release-asset.mjs';

const pkg = {name: '@robotics-runtime/host', private: true, version: '0.1.0-rc.0',
  engines: {node: '24.21.0', npm: '11.19.0'},
  exports: {'.': {import: './dist/src/index.js', types: './dist/src/index.d.ts'}}};
const input = {candidate: 'host-v0.1.0-rc.0', event: 'workflow_dispatch',
  source_revision: 'a'.repeat(40), source_tree: 'b'.repeat(40)};
test('candidate identity cannot name a different source package version', () => {
  assert.throws(() => makePlan(pkg, {...input, candidate: 'host-v0.1.0-rc.1'}), /committed host version/);
  assert.throws(() => makePlan({...pkg, private: false}, input), /registry publication/);
  assert.throws(() => makePlan({...pkg, name: '@foreign/host'}, input), /core host/);
});
test('source previews do not invent an accepted reference', () => {
  assert.equal(makePlan(pkg, input).reference, null);
  assert.throws(() => makePlan(pkg, {...input, reference_asset_sha256: 'c'.repeat(64)}), /incomplete/);
  assert.throws(() => makePlan(pkg, {...input, source_revision: 'main'}), /Git identity/);
});
async function fixture(work) {
  const directory = await mkdtemp(join(tmpdir(), 'host-release-guard-'));
  try {
    const raw = Buffer.from('opaque archive fixture; npm performs the actual archive install');
    const filename = 'robotics-runtime-host-0.1.0-rc.0.tgz';
    await writeFile(join(directory, filename), raw);
    const files = ['package.json', 'dist/src/index.js', 'dist/src/index.d.ts', 'schemas/a.json',
      'producers/a.py', 'proto/a.proto', 'tools/fetch-mavsdk-server.mjs', 'tools/mavsdk-server.v4.0.3.json'];
    const row = {name: pkg.name, version: pkg.version, filename,
      integrity: 'sha512-' + createHash('sha512').update(raw).digest('base64'),
      files: files.map(path => ({path}))};
    await work({directory, raw, row});
  } finally {await rm(directory, {recursive: true, force: true});}
}
test('reference match binds both the source tree and actual archive bytes', async () => fixture(async ({directory, raw, row}) => {
  const reference = {reference_revision: 'd'.repeat(40), reference_tree: input.source_tree,
    reference_asset_sha256: createHash('sha256').update(raw).digest('hex')};
  assert.equal((await verifyArtifact(pkg, makePlan(pkg, {...input, ...reference}), [row], directory)).reference_matches, true);
  assert.equal((await verifyArtifact(pkg, makePlan(pkg, {...input, ...reference, reference_tree: 'e'.repeat(40)}), [row], directory)).reference_matches, false);
  assert.equal((await verifyArtifact(pkg, makePlan(pkg, input), [row], directory)).reference_matches, false);
}));
test('published asset set cannot escape or silently include another file', async () => fixture(async ({directory, row}) => {
  await assert.rejects(verifyArtifact(pkg, makePlan(pkg, input), [{...row, filename: '../foreign.tgz'}], directory));
  await writeFile(join(directory, 'foreign.tgz'), 'unexpected');
  await assert.rejects(verifyArtifact(pkg, makePlan(pkg, input), [row], directory), /unexpected release asset/);
}));
test('workspace-only exports and replaced archives cannot satisfy packed identity', async () => fixture(async ({directory, row}) => {
  const missing = {...row, files: row.files.filter(file => file.path !== 'dist/src/index.js')};
  await assert.rejects(verifyArtifact(pkg, makePlan(pkg, input), [missing], directory), /export is missing/);
  await writeFile(join(directory, row.filename), 'replaced bytes');
  await assert.rejects(verifyArtifact(pkg, makePlan(pkg, input), [row], directory), /npm integrity differs/);
}));
test('corrupted reference metadata cannot manufacture a publish match', async () => fixture(async ({directory, row}) => {
  const plan = makePlan(pkg, input);
  await assert.rejects(verifyArtifact(pkg, {...plan, reference: {asset_sha256: 'c'.repeat(64)}}, [row], directory));
  await assert.rejects(verifyArtifact(pkg, {...plan, source_revision: 'main'}, [row], directory), /Git identity/);
}));
