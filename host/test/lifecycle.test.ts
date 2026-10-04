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
      let failed: RunStartupError | undefined;
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), (error: unknown) => {
        if (error instanceof RunStartupError) failed = error;
        assert.ok(error instanceof RunStartupError); assert.equal(error.completion.status, 'incomplete');
        assert.ok(error.completion.phases.some(item => item.phase === 'retained'));
        if (mode === 'not-ready') assert.ok(error.completion.resourceOutcomes.every(item => !item.attempted && !item.released));
        return true;
      });
      assert.ok(failed);
      const diagnostic = join(value.directory, 'startup-diagnostic.json');
      await writeFile(diagnostic, JSON.stringify({ error: failed.message }));
      const retried = await failed.run.retryExport(async () => [await referenceFile(diagnostic)]);
      assert.equal(retried.status, 'error');
      assert.ok(retried.resourceOutcomes.every(item => item.attempted && item.released));
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
      let failed: RunStartupError | undefined;
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), (error: unknown) => {
        if (error instanceof RunStartupError) failed = error;
        assert.ok(error instanceof RunStartupError);
        assert.match(error.message, /probe failed|deadline exceeded/);
        assert.equal(error.completion.status, 'incomplete');
        assert.ok(error.completion.resourceOutcomes.every(item => !item.attempted && !item.released));
        assert.ok(error.completion.phases.some(item => item.phase === 'preloading' && item.status === 'error'));
        return true;
      });
      assert.ok(failed);
      const diagnostic = join(value.directory, 'startup-diagnostic.json');
      await writeFile(diagnostic, JSON.stringify({ error: failed.message }));
      const retried = await failed.run.retryExport(async () => [await referenceFile(diagnostic)]);
      assert.equal(retried.status, 'error');
      assert.ok(retried.resourceOutcomes.every(item => item.attempted && item.released));
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

test('invalid deadline is refused before starting any provider effect', async () => {
  const { setTimeout: pause } = await import('node:timers/promises');
  for (const deadlineMs of [0, -1, 0.5, 2147483648]) {
    const value = await fixture(); const ctx = await host([{ ...value.descriptor, deadlineMs }]);
    try {
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /invalid lifecycle deadline/);
      await pause(100);
      await assert.rejects(access(value.resourcePath));
      await assert.rejects(access(value.readyPath));
    } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
  }
});

test('owner ID remains reserved throughout delayed native cleanup and verification', async () => {
  const { setTimeout: pause } = await import('node:timers/promises');
  const value = await fixture();
  const modulePath = join(value.directory, 'provider.mjs');
  await chmod(modulePath, 0o644);
  await writeFile(modulePath, (await readFile(modulePath, 'utf8')).replace('cleanup:async()=>{', 'cleanup:async()=>{await new Promise(done=>setTimeout(done,250));'));
  await chmod(modulePath, 0o444);
  const identity = await referenceFile(modulePath);
  const descriptor = { ...value.descriptor, files: value.descriptor.files.map(file => file.path === modulePath ? { ...file, sha256: identity.sha256 } : file) };
  const ctx = await host([descriptor]);
  try {
    const first = await ctx.runOwner.start(value.runId, value.runId); first.beginMeasurement();
    const finishing = first.finish(hooks(first, value.directory, []));
    await pause(40);
    await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
    assert.equal((await finishing).status, 'passed');
    const second = await ctx.runOwner.start(value.runId, value.runId); second.beginMeasurement();
    await access(value.resourcePath);
    assert.equal((await second.finish(hooks(second, value.directory, []))).status, 'passed');
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});

test('failed export retains raw resource and owner until explicit export retry completes cleanup', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const stages = hooks(run, value.directory, []);
    const incomplete = await run.finish({ ...stages, exportEvidence: async () => { throw new Error('export storage unavailable'); } });
    assert.equal(incomplete.status, 'incomplete'); assert.equal(run.phase, 'retained');
    assert.ok(incomplete.errors.includes('export storage unavailable'));
    assert.ok(incomplete.resourceOutcomes.every(item => !item.attempted && !item.released));
    await access(value.resourcePath);
    await assert.rejects(access(join(value.directory, 'retained-resource.bin')));
    await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
    const retried = await run.retryExport(stages.exportEvidence);
    assert.equal(retried.status, 'error');
    assert.ok(retried.errors.includes('export storage unavailable'));
    assert.ok(retried.resourceOutcomes.every(item => item.attempted && item.released));
    await assert.rejects(access(value.resourcePath));
    await access(join(value.directory, 'retained-resource.bin'));
    await access(value.cleanupPath);
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});
