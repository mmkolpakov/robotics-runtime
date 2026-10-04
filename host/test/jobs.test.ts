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
