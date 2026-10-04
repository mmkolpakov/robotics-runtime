import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Context } from 'cordis';
import { Jobs } from '../src/plugins/jobs/index.js';
test('finite argv, exits, spawn errors, timeout, output limit and cancellation', async () => {
  const ctx = new Context();
  const fiber = ctx.plugin(Jobs, { timeoutMs: 2000, maxBufferBytes: 4096, killTimeoutMs: 100 });
  await fiber.await();
  try {
    const literal = '$(touch forbidden); spaces & quotes';
    const success = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'process.stdout.write(process.argv[1])', literal] });
    assert.equal(success.stdout, literal); assert.equal(success.ok, true);
    const failed = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'process.stderr.write("failure detail"); process.exit(7)'] });
    assert.equal(failed.exitCode, 7); assert.equal(failed.stderr, 'failure detail'); assert.equal(failed.ok, false);
    const missing = await ctx.jobs.run({ executable: '/rr-does-not-exist', args: [] });
    assert.equal(missing.code, 'ENOENT'); assert.equal(missing.ok, false);
    const timeout = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'setInterval(()=>{},100)'], timeoutMs: 80 });
    assert.equal(timeout.timedOut, true); assert.equal(timeout.ok, false);
    const overflow = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'process.stdout.write("x".repeat(8192))'] });
    assert.equal(overflow.ok, false); assert.match(overflow.diagnostic ?? '', /maxBuffer/);
    const abort = new AbortController();
    const canceled = ctx.jobs.run({ executable: process.execPath, args: ['-e', 'setInterval(()=>{},100)'], cancelSignal: abort.signal });
    abort.abort(); assert.equal((await canceled).canceled, true);
    assert.throws(() => ctx.jobs.run({ executable: process.execPath, args: [], timeoutMs: 0 }), RangeError);
    assert.throws(() => ctx.jobs.run({ executable: process.execPath, args: [], maxBufferBytes: 5000 }), RangeError);
  } finally { await fiber.dispose(); }
});
test('disposing jobs owner cancels and reaps its child', async () => {
  const ctx = new Context(); const fiber = ctx.plugin(Jobs); await fiber.await();
  const child = ctx.jobs.run({ executable: process.execPath, args: ['-e', 'setInterval(()=>{},100)'] });
  await fiber.dispose(); assert.equal((await child).canceled, true);
});

test('worker environment withholds inherited secrets and admits explicit values', async () => {
  const ctx = new Context(); const fiber = ctx.plugin(Jobs); await fiber.await();
  process.env.RR_PARENT_PRIVATE_SENTINEL = 'private-sentinel';
  try {
    const withheld = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'process.stdout.write(String(Object.hasOwn(process.env,"RR_PARENT_PRIVATE_SENTINEL")))'] });
    assert.equal(withheld.stdout, 'false');
    const explicit = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'process.stdout.write(process.env.RR_ALLOWED_VALUE ?? "")'], env: { RR_ALLOWED_VALUE: 'approved' } });
    assert.equal(explicit.stdout, 'approved');
  } finally { delete process.env.RR_PARENT_PRIVATE_SENTINEL; await fiber.dispose(); }
});

test('native Execa killDescendants cancels the observed process group', async () => {
  const { mkdtemp, readFile, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { setTimeout: pause } = await import('node:timers/promises');
  const directory = await mkdtemp(join(tmpdir(), 'rr-descendants-'));
  const pidPath = join(directory, 'pid');
  const ctx = new Context(); const fiber = ctx.plugin(Jobs, { timeoutMs: 5000 }); await fiber.await();
  const abort = new AbortController();
  let pid: number | undefined;
  try {
    const child = ctx.jobs.run({ executable: process.execPath, cancelSignal: abort.signal, args: ['-e',
      'const {spawn}=require("node:child_process"); const fs=require("node:fs"); const child=spawn(process.execPath,["-e","setInterval(()=>{},100)"],{stdio:"ignore"}); fs.writeFileSync(process.argv[1],String(child.pid)); setInterval(()=>{},100);',
      pidPath] });
    for (let attempt = 0; attempt < 100; attempt++) {
      try { pid = Number(await readFile(pidPath, 'utf8')); break; } catch { await pause(10); }
    }
    assert.ok(pid && Number.isSafeInteger(pid));
    process.kill(pid, 0);
    abort.abort();
    assert.equal((await child).canceled, true);
    let terminated = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      try { process.kill(pid, 0); } catch { terminated = true; break; }
      await pause(10);
    }
    assert.equal(terminated, true, 'the observed descendant must no longer exist');
  } finally {
    abort.abort(); await fiber.dispose();
    if (pid) { try { process.kill(pid, 'SIGKILL'); } catch {} }
    await rm(directory, { recursive: true, force: true });
  }
});
