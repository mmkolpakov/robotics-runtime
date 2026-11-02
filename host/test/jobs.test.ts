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
test('disposing jobs owner cancels and reaps both text and raw children', async () => {
  const ctx = new Context(); const fiber = ctx.plugin(Jobs); await fiber.await();
  const request = { executable: process.execPath, args: ['-e', 'setInterval(()=>{},100)'] };
  const text = ctx.jobs.run(request); const raw = ctx.jobs.runBytes(request);
  await fiber.dispose();
  assert.equal((await text).canceled, true); assert.equal((await raw).canceled, true);
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

for (const method of ['run', 'runBytes'] as const) {
test(`native Execa killDescendants cancels the observed process group (${method})`, async () => {
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
    const child = ctx.jobs[method]({ executable: process.execPath, cancelSignal: abort.signal, args: ['-e',
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
}

for (const method of ['run', 'runBytes'] as const) {
test(`output overflow stops the live worker and its owned descendant (${method})`, { skip: process.platform !== 'linux' }, async () => {
  const { mkdtemp, readFile, writeFile, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { setTimeout: pause } = await import('node:timers/promises');
  const directory = await mkdtemp(join(tmpdir(), 'rr-overflow-'));
  const pidsPath = join(directory, 'pids.json');
  const releasePath = join(directory, 'release');
  const ctx = new Context();
  const fiber = ctx.plugin(Jobs, { timeoutMs: 10000, maxBufferBytes: 4096, killTimeoutMs: 100 });
  await fiber.await();
  type Identity = { pid: number; start: string };
  const identities: Identity[] = [];
  async function state(pid: number): Promise<{ state: string; start: string } | undefined> {
    try {
      const stat = await readFile('/proc/' + pid + '/stat', 'utf8');
      const fields = stat.slice(stat.lastIndexOf(')') + 2).split(' ');
      return { state: fields[0]!, start: fields[19]! };
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return undefined;
      throw error;
    }
  }
  try {
    const job = ctx.jobs[method]({ executable: process.execPath, args: ['-e',
      'const {spawn}=require("node:child_process"); const fs=require("node:fs"); const child=spawn(process.execPath,["-e","setInterval(()=>{},100)"],{stdio:"ignore"}); fs.writeFileSync(process.argv[1]+".tmp",JSON.stringify([process.pid,child.pid])); fs.renameSync(process.argv[1]+".tmp",process.argv[1]); let emitted=false; setInterval(()=>{if(!emitted && fs.existsSync(process.argv[2])){emitted=true; process.stdout.write("x".repeat(8192));}},10);',
      pidsPath, releasePath] });
    let pids: number[] | undefined;
    for (let attempt = 0; attempt < 100; attempt++) {
      try { pids = JSON.parse(await readFile(pidsPath, 'utf8')) as number[]; break; }
      catch (error) {
        if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
        await pause(10);
      }
    }
    assert.equal(pids?.length, 2);
    for (const pid of pids!) {
      assert.ok(Number.isSafeInteger(pid) && pid > 1);
      const observed = await state(pid);
      assert.ok(observed && observed.state !== 'Z', 'worker and descendant must be alive before overflow');
      identities.push({ pid, start: observed.start });
    }
    await writeFile(releasePath, '');
    const result = await Promise.race([job, pause(3000, undefined, { ref: false }).then(() => undefined)]);
    assert.ok(result, 'overflow must settle before the job deadline without cancellation');
    assert.ok(result.durationMs < 9000, 'overflow must settle before the total job deadline');
    assert.equal(result.ok, false);
    assert.match(result.diagnostic ?? '', /maxBuffer/);
    assert.equal(result.timedOut, false, 'overflow must stop the worker before its deadline');
    assert.equal(result.canceled, false, 'overflow must not depend on external cancellation');
    for (const [index, identity] of identities.entries()) {
      let exited = false;
      for (let attempt = 0; attempt < 100; attempt++) {
        const observed = await state(identity.pid);
        if (!observed || observed.start !== identity.start || observed.state === 'Z') { exited = true; break; }
        await pause(10);
      }
      assert.equal(exited, true, index === 0 ? 'worker must exit' : 'descendant must exit');
    }
  } finally {
    await fiber.dispose();
    for (const identity of identities) {
      const observed = await state(identity.pid);
      if (observed && observed.start === identity.start && observed.state !== 'Z') {
        try { process.kill(identity.pid, 'SIGKILL'); } catch (error) {
          if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error;
        }
      }
    }
    await rm(directory, { recursive: true, force: true });
  }
});
}

test('raw streams preserve invalid UTF-8, NUL and every final newline independently', async () => {
  const { createHash } = await import('node:crypto');
  const ctx = new Context(); const fiber = ctx.plugin(Jobs); await fiber.await();
  try {
    const expected = new Uint8Array([0, 255, 195, 40, 13, 10, 10]);
    const diagnostic = new Uint8Array([101, 255, 13, 10]);
    const result = await ctx.jobs.runBytes({ executable: process.execPath, args: ['-e',
      'process.stdout.write(Buffer.from([0,255,195,40,13,10,10])); process.stderr.write(Buffer.from([101,255,13,10]));'] });
    assert.equal(result.ok, true); assert.equal(result.isMaxBuffer, false);
    assert.equal(result.stdout.constructor, Uint8Array); assert.equal(result.stderr.constructor, Uint8Array);
    assert.deepEqual(result.stdout, expected); assert.deepEqual(result.stderr, diagnostic);
    assert.equal(createHash('sha256').update(result.stdout).digest('hex'), createHash('sha256').update(expected).digest('hex'));
    const text = await ctx.jobs.run({ executable: process.execPath, args: ['-e', 'process.stdout.write("text\\n")'] });
    assert.equal(text.stdout, 'text'); assert.equal(typeof text.stdout, 'string');
    assert.equal(Object.hasOwn(text, 'isMaxBuffer'), false);
  } finally { await fiber.dispose(); }
});

test('raw JSON retains the exact uint64 numeric token and trailing CRLF', async () => {
  const ctx = new Context(); const fiber = ctx.plugin(Jobs); await fiber.await();
  try {
    const original = '{"value":18446744073709551615}\r\n\n';
    const result = await ctx.jobs.runBytes({ executable: process.execPath,
      args: ['-e', 'process.stdout.write(process.argv[1])', original] });
    assert.equal(result.ok, true);
    assert.deepEqual(result.stdout, new TextEncoder().encode(original));
  } finally { await fiber.dispose(); }
});

test('raw limits count multibyte output bytes and bound stderr separately', async () => {
  const ctx = new Context();
  const fiber = ctx.plugin(Jobs, { maxBufferBytes: 32, killTimeoutMs: 100 }); await fiber.await();
  try {
    const request = { executable: process.execPath, args: ['-e', 'process.stdout.write("\\u00e9".repeat(4))'] };
    const exact = await ctx.jobs.runBytes({ ...request, maxBufferBytes: 8 });
    assert.equal(exact.ok, true); assert.equal(exact.stdout.byteLength, 8);
    const tooLarge = await ctx.jobs.runBytes({ ...request, maxBufferBytes: 7 });
    assert.equal(tooLarge.ok, false); assert.equal(tooLarge.isMaxBuffer, true);
    assert.ok(tooLarge.stdout.byteLength <= 7);
    const stderr = await ctx.jobs.runBytes({ executable: process.execPath,
      args: ['-e', 'process.stdout.write("{}"); process.stderr.write("\\u00e9".repeat(2))'],
      maxBufferBytes: 32, stderrMaxBufferBytes: 3 });
    assert.equal(stderr.ok, false); assert.equal(stderr.isMaxBuffer, true);
    assert.ok(stderr.stderr.byteLength <= 3);
    for (const value of [0, -1, 1.5, 33, Number.POSITIVE_INFINITY]) {
      assert.throws(() => ctx.jobs.runBytes({ ...request, stderrMaxBufferBytes: value }), RangeError);
    }
  } finally { await fiber.dispose(); }
});

test('a parseable JSON prefix after raw overflow is still a failed capture', async () => {
  const ctx = new Context();
  const fiber = ctx.plugin(Jobs, { maxBufferBytes: 128, killTimeoutMs: 100 }); await fiber.await();
  try {
    const result = await ctx.jobs.runBytes({ executable: process.execPath, args: ['-e',
      'process.stdout.write("{}\\n"+" ".repeat(16384))'] });
    assert.equal(result.ok, false); assert.equal(result.isMaxBuffer, true);
    assert.ok(result.stdout.byteLength <= 128);
    assert.deepEqual(JSON.parse(Buffer.from(result.stdout).toString('utf8')), {});
  } finally { await fiber.dispose(); }
});

test('raw spawn failure, nonzero exit and timeout retain process outcomes', async () => {
  const ctx = new Context(); const fiber = ctx.plugin(Jobs, { timeoutMs: 2000, killTimeoutMs: 100 }); await fiber.await();
  try {
    const failed = await ctx.jobs.runBytes({ executable: process.execPath,
      args: ['-e', 'process.stderr.write("detail\\n"); process.exit(7)'] });
    assert.equal(failed.ok, false); assert.equal(failed.exitCode, 7);
    assert.equal(failed.isMaxBuffer, false);
    assert.deepEqual(failed.stderr, new TextEncoder().encode('detail\n'));
    const missing = await ctx.jobs.runBytes({ executable: '/rr-does-not-exist', args: [] });
    assert.equal(missing.ok, false); assert.equal(missing.code, 'ENOENT');
    assert.deepEqual(missing.stdout, new Uint8Array());
    const timeout = await ctx.jobs.runBytes({ executable: process.execPath,
      args: ['-e', 'setInterval(()=>{},100)'], timeoutMs: 80 });
    assert.equal(timeout.ok, false); assert.equal(timeout.timedOut, true);
    assert.equal(timeout.isMaxBuffer, false);
  } finally { await fiber.dispose(); }
});
