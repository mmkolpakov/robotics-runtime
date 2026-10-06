import assert from 'node:assert/strict';
import test from 'node:test';
import {mkdtemp, mkdir, readFile, readdir, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {makePlan, verifyArtifact, requirePublicationCommit} from './release-asset.mjs';

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

test('a moved public tag cannot reuse compiled tree or artifact equality', () => {
  const built = 'a'.repeat(40), moved = 'b'.repeat(40);
  requirePublicationCommit(built, built, built);
  assert.throws(() => requirePublicationCommit(built, built, moved), /remote tag moved/);
  assert.throws(() => requirePublicationCommit(built, moved, built), /tag-trigger commit/);
  assert.throws(() => requirePublicationCommit(built, built, ''), /exact publication commit/);
});

const draftAssets = ['robotics-runtime-host-0.1.0-rc.0.tgz', 'manifest.json',
  'SHA256SUMS', 'consumer-package-lock.json', 'consumer.json'];
async function draftFixture(change, accepted) {
  const root = await mkdtemp(join(tmpdir(), 'host-draft-retry-'));
  try {
    const remote = join(root, 'remote'), temporary = join(root, 'temporary'), bin = join(root, 'bin');
    for (const directory of [remote, temporary, bin, join(root, 'release/dist')]) await mkdir(directory, {recursive: true});
    for (const name of draftAssets) {
      const local = join(root, name.endsWith('.tgz') ? 'release/dist' : 'release', name);
      await writeFile(local, 'this run: ' + name);
      await writeFile(join(remote, name), await readFile(local));
    }
    await change(remote);
    const snapshot = async () => Promise.all((await readdir(remote)).sort().map(async name =>
      [name, (await readFile(join(remote, name))).toString('base64')]));
    const before = await snapshot();
    await writeFile(join(bin, 'gh'), "#!/usr/bin/env bash\nset -euo pipefail\ntest \"$1\" = release\ncommand=\"$2\"\ntest \"$3\" = \"$CANDIDATE\"\nshift 3\ncase \"$command\" in\n  download)\n    test \"$1\" = --dir\n    directory=\"$2\"\n    shift 2\n    for name in \"$ASSET\" manifest.json SHA256SUMS consumer-package-lock.json consumer.json; do\n      test \"$1\" = --pattern\n      test \"$2\" = \"$name\"\n      shift 2\n      if [[ -f \"$REMOTE/$name\" ]]; then cp \"$REMOTE/$name\" \"$directory/$name\"; fi\n    done\n    test \"$#\" = 0\n    ;;\n  view)\n    test \"$*\" = \"--json assets --jq .assets[].name\"\n    for file in \"$REMOTE\"/*; do\n      if [[ -f \"$file\" ]]; then basename \"$file\"; fi\n    done\n    ;;\n  *) exit 99 ;;\nesac\n", {mode: 0o700});
    const workflow = await readFile(new URL('../../.github/workflows/host-release.yml', import.meta.url), 'utf8');
    const start = workflow.indexOf('          check_draft_assets() (');
    const end = workflow.indexOf('\n          )\n', start);
    assert.ok(start >= 0 && end > start, 'actual workflow draft function is required');
    const actualFunction = workflow.slice(start, end + '\n          )'.length).replace(/^          /gm, '');
    const result = spawnSync('bash', ['-Eeuo', 'pipefail', '-c',
      actualFunction + '\ncheck_draft_assets\nprintf accepted > accepted\n'], {
      cwd: root, encoding: 'utf8', env: {...process.env, PATH: bin + ':' + process.env.PATH,
        RUNNER_TEMP: temporary, REMOTE: remote, ASSET: draftAssets[0], CANDIDATE: input.candidate},
    });
    assert.equal(result.error, undefined);
    assert.equal(result.status === 0, accepted, result.stderr);
    assert.equal((await readdir(root)).includes('accepted'), accepted);
    assert.deepEqual(await snapshot(), before, 'remote draft assets must never be repaired or replaced');
    assert.deepEqual(await readdir(temporary), [], 'fresh downloads are cleaned on success and refusal');
  } finally {await rm(root, {recursive: true, force: true});}
}
test('complete identical draft is accepted without remote mutation', () => draftFixture(async () => {}, true));
test('partial upload draft is refused before staged success', () => draftFixture(async remote => {
  for (const name of draftAssets.slice(1)) await rm(join(remote, name));
}, false));
test('stale draft manifest is refused despite matching asset names', () => draftFixture(async remote => {
  await writeFile(join(remote, 'manifest.json'), 'earlier source');
}, false));
test('one missing draft asset cannot be accepted', () => draftFixture(async remote => {
  await rm(join(remote, 'consumer.json'));
}, false));
test('surplus remote draft asset cannot be silently ignored', () => draftFixture(async remote => {
  await writeFile(join(remote, 'extra.json'), 'surplus');
}, false));
