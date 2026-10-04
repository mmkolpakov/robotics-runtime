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
