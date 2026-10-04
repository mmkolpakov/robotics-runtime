import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, chmod, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomUUID, createHash } from 'node:crypto';
import { Context } from 'cordis';
import { Admission } from '../src/plugins/admission/index.js';
import type { TrustedProfile } from '../src/plugins/admission/index.js';
import { RunOwner, RunStartupError } from '../src/plugins/run-owner/index.js';
import type { OwnedRun } from '../src/plugins/run-owner/index.js';
import { referenceFile } from '../src/plugins/application-lifecycle/index.js';
import type { CompletionHooks } from '../src/plugins/application-lifecycle/index.js';

import { fixture, host, hooks } from './lifecycle-support.js';

test('immutable admission rejects unknown selection, mutable files, digest tamper and forged profiles', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  try {
    await assert.rejects(ctx.admission.admit('operator-module'), /not trusted/);
    assert.throws(() => ctx.admission.assertIssued({ ...value.descriptor, profileSha256: '0'.repeat(64) }), /not admitted/);
    await chmod(value.profilePath, 0o644);
    await assert.rejects(ctx.admission.admit(value.runId), /immutable/);
    await writeFile(value.profilePath, '# tamper\n'); await chmod(value.profilePath, 0o444);
    await assert.rejects(ctx.admission.admit(value.runId), /digest mismatch/);
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});

test('required missing import, PENDING and false backend probe are rejected with complete teardown reports', async () => {
  for (const mode of ['missing', 'pending', 'not-ready'] as const) {
    const value = await fixture(mode); const ctx = await host([value.descriptor]);
    try {
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), (error: unknown) => {
        assert.ok(error instanceof RunStartupError); assert.equal(error.completion.status, 'error');
        assert.ok(error.completion.phases.some(item => item.phase === 'verifying-cleanup'));
        if (mode === 'not-ready') assert.ok(error.completion.resourceOutcomes.every(item => item.released));
        return true;
      });
    } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
  }
});

test('preload and measurement are distinct; evidence precedes destructive cleanup and survives it', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId);
    assert.equal(run.phase, 'ready'); assert.equal(ctx.get('backend'), undefined);
    run.beginMeasurement(); assert.equal(run.phase, 'measuring');
    const trace: string[] = [];
    const completion = await run.finish(hooks(run, value.directory, trace));
    assert.deepEqual(trace, ['close', 'capture', 'drain', 'export']);
    assert.equal(completion.status, 'passed');
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
    await assert.rejects(access(value.resourcePath));
    await access(join(value.directory, 'capture.json')); await access(value.cleanupPath);
    assert.equal(await run.finish(), completion);
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});

test('resolved Cordis dispose cannot hide physical cleanup or caught native effect errors', async () => {
  for (const mode of ['bad-cleanup', 'logged-cleanup'] as const) {
    const value = await fixture(mode); const ctx = await host([value.descriptor]);
    try {
      const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
      const completion = await run.finish(hooks(run, value.directory, []));
      assert.equal(completion.status, 'error');
      assert.ok(completion.errors.some(error => /cleanup failure/.test(error)));
      if (mode === 'bad-cleanup') {
        assert.equal(completion.resourceOutcomes[0]?.released, false); await access(value.resourcePath);
      } else { assert.equal(completion.resourceOutcomes[0]?.released, true); }
      await access(value.readyPath); await access(value.cleanupPath);
    } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
  }
});

test('two owners have isolated bindings; disposing one leaves the other resource active', async () => {
  const first = await fixture(); const second = await fixture(); const ctx = await host([first.descriptor, second.descriptor]);
  try {
    const a = await ctx.runOwner.start(first.runId, first.runId); const b = await ctx.runOwner.start(second.runId, second.runId);
    assert.notEqual(a.context.get('backend'), b.context.get('backend'));
    assert.throws(() => a.resources.track({ id: 'foreign', ownerId: second.runId, cleanup: async () => {}, verifyCleanup: async () => ({ released: true, evidenceRefs: [] }) }), /foreign/);
    a.beginMeasurement(); b.beginMeasurement();
    assert.equal((await a.finish(hooks(a, first.directory, []))).status, 'passed'); await access(second.resourcePath);
    assert.equal((await b.finish(hooks(b, second.directory, []))).status, 'passed');
  } finally { await ctx.fiber.dispose(); await rm(first.directory, { recursive: true, force: true }); await rm(second.directory, { recursive: true, force: true }); }
});

test('native readiness callback error and timeout remain errors with independent cleanup', async () => {
  for (const mode of ['probe-error', 'probe-timeout'] as const) {
    const value = await fixture(mode); const ctx = await host([value.descriptor]);
    try {
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), (error: unknown) => {
        assert.ok(error instanceof RunStartupError);
        assert.match(error.message, /probe failed|deadline exceeded/);
        assert.equal(error.completion.status, 'error');
        assert.ok(error.completion.resourceOutcomes.every(item => item.attempted && item.released));
        assert.ok(error.completion.phases.some(item => item.phase === 'preloading' && item.status === 'error'));
        return true;
      });
    } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
  }
});

test('failed measurement close still retains export and cleanup evidence without successful completion', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const steps = hooks(run, value.directory, []);
    const completion = await run.finish({ ...steps, closeMeasurement: async () => { throw new Error('measurement aborted'); } });
    assert.equal(completion.status, 'error');
    assert.ok(completion.errors.includes('measurement aborted'));
    await access(join(value.directory, 'retained-resource.bin'));
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});

test('same run ID is reserved before asynchronous admission', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  try {
    const started = ctx.runOwner.start(value.runId, value.runId);
    await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
    const run = await started; run.beginMeasurement();
    assert.equal((await run.finish(hooks(run, value.directory, []))).status, 'passed');
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});
