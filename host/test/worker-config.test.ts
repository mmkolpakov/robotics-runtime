import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Context, FiberState } from 'cordis';
import { Jobs } from '../src/plugins/jobs/index.js';
import { Documents } from '../src/plugins/documents/index.js';
import { Evaluation } from '../src/plugins/evaluation/index.js';

test('document and evaluation configuration fails before providing a launchable service', async () => {
  const ctx = new Context(); await ctx.plugin(Jobs);
  try {
    for (const plugin of [Documents, Evaluation]) {
      for (const config of [undefined, { executable: '' }, { executable: '   ' }]) {
        // Registry's public API can receive undefined from an omitted Include config.
        const fiber = ctx.registry.plugin(plugin, config);
        await assert.rejects(fiber.await(), /configured worker executable is required/);
        assert.equal(fiber.state, FiberState.FAILED);
        assert.equal(ctx.get(plugin === Documents ? 'documents' : 'evaluation'), undefined);
        await fiber.dispose();
      }
    }
  } finally { await ctx.fiber.dispose(); }
});

test('nanosecond API rejects runtime numbers and coercible objects before worker launch', async () => {
  const { mkdtemp, access, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const directory = await mkdtemp(join(tmpdir(), 'rr-exact-ns-'));
  const marker = join(directory, 'launched');
  const ctx = new Context(); await ctx.plugin(Jobs);
  await ctx.plugin(Evaluation, { executable: process.execPath, prefixArgs: ['-e',
    'require("node:fs").writeFileSync(process.argv[1],"launched"); process.stdout.write(process.argv.slice(2).join("|"));', marker, '--'] });
  const input = { scenario: 'scenario', runtime: 'runtime', runId: 'run', domainId: 'domain', runContext: 'context',
    evidenceIndex: 'evidence', otelMetrics: 'metrics', windowStartNs: '9007199254740993', windowEndNs: '9007200254740993',
    outputDirectory: 'output', diagnosticOutput: 'diagnostic' };
  let coerced = false;
  try {
    for (const value of [42, 9007199254740993, null, undefined, { toString: () => { coerced = true; return '42'; } }]) {
      assert.throws(() => ctx.evaluation.evaluate({ ...input, windowStartNs: value as unknown as string }), /JavaScript numbers are rejected/);
    }
    assert.equal(coerced, false); await assert.rejects(access(marker));
    const decimal = await ctx.evaluation.evaluate(input);
    assert.equal(decimal.ok, true, decimal.stderr); assert.match(decimal.stdout, /9007199254740993/);
    const integer = await ctx.evaluation.evaluate({ ...input, windowStartNs: 9007199254740993n });
    assert.equal(integer.ok, true); assert.match(integer.stdout, /9007199254740993/);
  } finally { await ctx.fiber.dispose(); await rm(directory, { recursive: true, force: true }); }
});
