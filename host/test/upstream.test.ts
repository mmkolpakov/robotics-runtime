import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { promisify } from 'node:util';
import { execFile } from 'node:child_process';
import { Context, FiberState, Service } from 'cordis';
import type { Plugin } from 'cordis';
import { Include } from '@cordisjs/plugin-include';
import { createHost } from '../src/host.js';

const run = promisify(execFile);
const fixtureUrl = new URL('./fixtures/provider.js', import.meta.url).href;

test('strict public API: native service, injection, effect, isolation and dispose', async () => {
  const ctx = new Context();
  const marks: string[] = [];
  class Backend extends Service {
    constructor(scope: Context) { super(scope, 'testBackend'); }
    async *[Service.init]() {
      marks.push('ready');
      yield async () => { marks.push('closed'); };
    }
  }
  const isolated = ctx.isolate('testBackend', Symbol('run-a'));
  const other = ctx.isolate('testBackend', Symbol('run-b'));
  const backend = isolated.plugin(Backend);
  await backend.await();
  assert.equal(backend.state, FiberState.ACTIVE);
  assert.ok(isolated.get('testBackend'));
  assert.equal(other.get('testBackend'), undefined);
  const pendingPlugin: Plugin.Function<void> = () => { throw new Error('must not execute'); };
  pendingPlugin.inject = ['absentBackend'];
  const pending = isolated.plugin(pendingPlugin);
  await pending.await();
  assert.equal(pending.state, FiberState.PENDING);
  await pending.dispose();
  await backend.dispose();
  assert.deepEqual(marks, ['ready', 'closed']);
});

test('native Include loads compiled ESM and !!js from trusted configuration', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'rr-host-include-'));
  const ctx = await createHost({ baseDirectory: directory });
  try {
    await writeFile(join(directory, 'cordis.yml'),
      `- id: fixture\n  name: "${fixtureUrl}"\n  config:\n    marker: !!js "'native-' + 'esm'"\n`);
    const id = await ctx.loader.create({ name: '@cordisjs/plugin-include', config: { path: './cordis.yml' } });
    const entry = ctx.loader.resolve(id);
    assert.ok(entry.fiber);
    await entry.fiber.await();
    assert.equal(entry.fiber.state, FiberState.ACTIVE);
    const include = entry.subtree;
    assert.ok(include instanceof Include);
    await include.await();
    assert.equal(include.resolve('fixture').fiber?.state, FiberState.ACTIVE);
    assert.equal(ctx.get('hostFixture').marker, 'native-esm');
  } finally {
    await ctx.fiber.dispose();
    await rm(directory, { recursive: true, force: true });
  }
});

test('failed import is observable as a missing Fiber, never readiness', async () => {
  const ctx = await createHost({ baseDirectory: process.cwd() });
  try {
    const id = await ctx.loader.create({ name: './missing-immutable-provider.js' });
    await ctx.loader.await();
    assert.equal(ctx.loader.resolve(id).fiber, undefined);
    assert.ok(ctx.logger.buffer.some(message => message.type === 'error'));
  } finally { await ctx.fiber.dispose(); }
});

test('upstream cordis CLI reads cwd/cordis.yml', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'rr-host-cli-'));
  try {
    const cli = join(dirname(createRequire(import.meta.url).resolve('cordis/package.json')), 'bin.js');
    await writeFile(join(directory, 'cordis.yml'),
      `- id: console\n  name: "@cordisjs/plugin-logger-console"\n  config: { colors: false }\n- id: fixture\n  name: "${fixtureUrl}"\n  config: { marker: cli, announce: true }\n`);
    // Config resolves packages from this trusted project's closure.
    await writeFile(join(directory, 'package.json'), '{"type":"module"}');
    const { symlink } = await import('node:fs/promises');
    await symlink(join(process.cwd(), 'node_modules'), join(directory, 'node_modules'), 'dir');
    const result = await run(process.execPath, [cli], { cwd: directory, timeout: 5000 });
    assert.match(result.stdout + result.stderr, /native profile loaded cli/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
