import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, chmod, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
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

test('settled native readiness callback error retains independent diagnostic recovery', async () => {
  for (const mode of ['probe-error'] as const) {
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

test('already canceled startup creates no provider effect and does not reserve its owner ID', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  const cancel = new AbortController(); cancel.abort(new Error('operator canceled before startup'));
  try {
    await assert.rejects(ctx.runOwner.start(value.runId, value.runId, { cancelSignal: cancel.signal }), /operator canceled before startup/);
    await assert.rejects(access(value.resourcePath));
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    assert.equal((await run.finish(hooks(run, value.directory, []))).status, 'passed');
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});

test('startup cancellation reaches the native probe and retains resources until diagnostic export', async () => {
  const { setTimeout: pause } = await import('node:timers/promises');
  const value = await fixture('probe-cancel'); const ctx = await host([value.descriptor]);
  const cancel = new AbortController();
  try {
    const options = { cancelSignal: cancel.signal };
    const started = ctx.runOwner.start(value.runId, value.runId, options);
    options.cancelSignal = new AbortController().signal;
    let failed: RunStartupError | undefined;
    const rejected = assert.rejects(started, (error: unknown) => {
      assert.ok(error instanceof RunStartupError);
      failed = error; assert.match(error.message, /operator canceled during startup/);
      assert.equal(error.completion.status, 'incomplete'); return true;
    });
    const deadline = performance.now() + 800;
    while (performance.now() < deadline) {
      try { await access(value.readyPath); break; } catch { await pause(10); }
    }
    assert.equal(await readFile(value.readyPath, 'utf8'), 'entered readiness probe');
    cancel.abort(new Error('operator canceled during startup'));
    await rejected; assert.ok(failed);
    assert.equal(failed.run.phase, 'retained'); await access(value.resourcePath);
    await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
    const diagnostic = join(value.directory, 'cancellation.json');
    await writeFile(diagnostic, JSON.stringify({ error: failed.message }));
    const completion = await failed.run.retryExport(async () => [await referenceFile(diagnostic)]);
    assert.equal(completion.status, 'error');
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
    await assert.rejects(access(value.resourcePath)); await access(diagnostic);
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});

test('canceled delayed Include cannot create a resource after retained export and cleanup', async () => {
  const { setTimeout: pause } = await import('node:timers/promises');
  const value = await fixture();
  const modulePath = join(value.directory, 'provider.mjs');
  await chmod(modulePath, 0o644);
  await writeFile(modulePath, "await new Promise(done => setTimeout(done, 180));\n" + await readFile(modulePath, 'utf8'));
  await chmod(modulePath, 0o444);
  const identity = await referenceFile(modulePath);
  const descriptor = { ...value.descriptor, files: value.descriptor.files.map(file => file.path === modulePath ? { ...file, sha256: identity.sha256 } : file) };
  const ctx = await host([descriptor]); const cancel = new AbortController();
  try {
    let failed: RunStartupError | undefined;
    const started = ctx.runOwner.start(value.runId, value.runId, { cancelSignal: cancel.signal });
    const rejected = assert.rejects(started, (error: unknown) => {
      assert.ok(error instanceof RunStartupError); failed = error; return true;
    });
    await pause(30); cancel.abort(new Error('operator canceled during Include import'));
    await rejected; assert.ok(failed); assert.equal(failed.run.phase, 'retained');
    const diagnostic = join(value.directory, 'delayed-include-cancellation.json');
    await writeFile(diagnostic, JSON.stringify({ error: failed.message }));
    const completion = await failed.run.retryExport(async () => [await referenceFile(diagnostic)]);
    assert.notEqual(completion.status, 'passed');
    await pause(250);
    await assert.rejects(access(value.resourcePath));
    await assert.rejects(access(value.readyPath));
    await access(diagnostic);
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});


const completionProducers = [
  ['closeMeasurement', 'close'], ['captureLastState', 'capture'],
  ['drainRecorders', 'drain'], ['exportEvidence', 'export'],
] as const;
for (const [key, name] of completionProducers) {
  test(`unsettled ${name} producer retains ownership and blocks export until explicit recovery`, async () => {
    const { setImmediate: nextTurn } = await import('node:timers/promises');
    const value = await fixture(); const ctx = await host([{ ...value.descriptor, deadlineMs: 250 }]);
    const release = Promise.withResolvers<void>(); const settled = Promise.withResolvers<void>();
    let signal: AbortSignal | undefined;
    try {
      const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
      const trace: string[] = []; const stages = hooks(run, value.directory, trace);
      const latePath = join(value.directory, `${name}-late.json`);
      const completion = await run.finish({ ...stages, [key]: async (cancel: AbortSignal) => {
        trace.push(name); signal = cancel;
        try {
          await release.promise;
          await writeFile(value.resourcePath, `late ${name} state`);
          await writeFile(latePath, JSON.stringify({ runId: run.runId, stage: name }));
          return [await referenceFile(latePath)];
        } finally { settled.resolve(); }
      } });
      const prefix = completionProducers.slice(0, completionProducers.findIndex(([stage]) => stage === key) + 1).map(([, stage]) => stage);
      assert.deepEqual(trace, prefix);
      assert.equal(signal?.aborted, true);
      assert.equal(completion.status, 'incomplete'); assert.equal(run.phase, 'retained');
      assert.ok(completion.errors.includes('lifecycle deadline exceeded'));
      assert.ok(completion.resourceOutcomes.every(item => !item.attempted && !item.released));
      await access(value.resourcePath);
      await assert.rejects(access(value.cleanupPath));
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
      const snapshot = structuredClone(completion);
      const blocked = await run.retryExport(stages.exportEvidence);
      assert.equal(blocked.status, 'incomplete'); assert.equal(run.phase, 'retained');
      assert.deepEqual(trace, prefix);
      await assert.rejects(access(join(value.directory, 'retained-resource.bin')));
      release.resolve(); await settled.promise; await nextTurn();
      assert.deepEqual(completion, snapshot);
      await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
      const recovered = await run.retryExport(stages.exportEvidence);
      assert.equal(recovered.status, 'error');
      assert.ok(recovered.errors.includes('lifecycle deadline exceeded'));
      assert.ok(recovered.resourceOutcomes.every(item => item.attempted && item.released));
      assert.ok(recovered.evidenceRefs.some(ref => ref.uri === pathToFileURL(latePath).href));
      assert.equal(await readFile(join(value.directory, 'retained-resource.bin'), 'utf8'), `late ${name} state`);
      assert.equal(trace.filter(item => item === name).length, key === 'exportEvidence' ? 2 : 1);
      assert.deepEqual(completion, snapshot);
      await assert.rejects(access(value.resourcePath));
    } finally {
      release.resolve();
      if (signal) await settled.promise;
      await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true });
    }
  });
}

test('late rejected export is retained in diagnostics and cannot overlap its explicit retry', async () => {
  const { setImmediate: nextTurn } = await import('node:timers/promises');
  const value = await fixture(); const ctx = await host([{ ...value.descriptor, deadlineMs: 250 }]);
  const release = Promise.withResolvers<void>(); const settled = Promise.withResolvers<void>();
  let entered = false;
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const trace: string[] = []; const stages = hooks(run, value.directory, trace);
    const incomplete = await run.finish({ ...stages, exportEvidence: async () => {
      entered = true;
      try { await release.promise; throw new Error('late export storage failure'); }
      finally { settled.resolve(); }
    } });
    assert.equal(incomplete.status, 'incomplete');
    assert.equal((await run.retryExport(stages.exportEvidence)).status, 'incomplete');
    assert.deepEqual(trace, ['close', 'capture', 'drain']);
    release.resolve(); await settled.promise; await nextTurn();
    const completion = await run.retryExport(stages.exportEvidence);
    assert.equal(completion.status, 'error');
    assert.ok(completion.errors.some(error => /late export storage failure/.test(error)));
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
    await access(join(value.directory, 'retained-resource.bin'));
  } finally {
    release.resolve(); if (entered) await settled.promise;
    await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true });
  }
});

test('timed-out late readiness cannot write after diagnostic export or lose its reserved owner', async () => {
  const { setImmediate: nextTurn } = await import('node:timers/promises');
  const value = await fixture('probe-timeout'); const ctx = await host([{ ...value.descriptor, deadlineMs: 250 }]);
  const provider = await import(pathToFileURL(join(value.directory, 'provider.mjs')).href) as {
    probe: { entered: PromiseWithResolvers<AbortSignal>; release: PromiseWithResolvers<void>; written: PromiseWithResolvers<void> };
  };
  try {
    let failed: RunStartupError | undefined;
    const started = ctx.runOwner.start(value.runId, value.runId);
    const rejected = assert.rejects(started, (error: unknown) => {
      assert.ok(error instanceof RunStartupError); failed = error;
      assert.match(error.message, /deadline exceeded/); assert.equal(error.completion.status, 'incomplete'); return true;
    });
    const signal = await provider.probe.entered.promise;
    await rejected; assert.ok(failed); assert.equal(signal.aborted, true);
    const snapshot = structuredClone(failed.completion);
    await access(value.resourcePath);
    let exported = false;
    const diagnostic = join(value.directory, 'late-startup-diagnostic.json');
    const exportDiagnostic = async () => {
      exported = true;
      await writeFile(diagnostic, JSON.stringify({ error: failed!.message }));
      return [await referenceFile(diagnostic)];
    };
    assert.equal((await failed.run.retryExport(exportDiagnostic)).status, 'incomplete');
    assert.equal(exported, false);
    await assert.rejects(access(value.cleanupPath)); await assert.rejects(access(diagnostic));
    await assert.rejects(ctx.runOwner.start(value.runId, value.runId), /already owned/);
    provider.probe.release.resolve(); await provider.probe.written.promise;
    // The native callback returns a byte reference only after its final write is captured.
    const settledDeadline = performance.now() + 1000;
    while (!failed.run.evidenceRefs.some(ref => ref.uri === pathToFileURL(value.readyPath).href) && performance.now() < settledDeadline) await nextTurn();
    assert.ok(failed.run.evidenceRefs.some(ref => ref.uri === pathToFileURL(value.readyPath).href));
    await nextTurn();
    assert.deepEqual(failed.completion, snapshot);
    const completion = await failed.run.retryExport(exportDiagnostic);
    assert.equal(completion.status, 'error'); assert.equal(exported, true);
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
    assert.ok(completion.evidenceRefs.some(ref => ref.uri === pathToFileURL(value.readyPath).href));
    await assert.rejects(access(value.resourcePath)); await access(diagnostic);
    assert.deepEqual(failed.completion, snapshot);
  } finally {
    provider.probe.release.resolve();
    await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true });
  }
});

test('cooperative cancellation settles the producer before subsequent stages and cleanup', async () => {
  const value = await fixture(); const ctx = await host([{ ...value.descriptor, deadlineMs: 250 }]);
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const trace: string[] = []; const stages = hooks(run, value.directory, trace);
    const completion = await run.finish({ ...stages, closeMeasurement: async signal => {
      trace.push('close');
      return await new Promise<readonly import('../src/plugins/application-lifecycle/index.js').ArtifactRef[]>((_, reject) => {
        signal.addEventListener('abort', () => { trace.push('close:settled'); reject(signal.reason); }, { once: true });
      });
    } });
    assert.deepEqual(trace, ['close', 'close:settled', 'capture', 'drain', 'export']);
    assert.equal(completion.status, 'error');
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});


test('enclosing Cordis disposal refuses owned-resource cleanup while a late producer remains active', async () => {
  const { setImmediate: nextTurn } = await import('node:timers/promises');
  const value = await fixture(); const ctx = await host([{ ...value.descriptor, deadlineMs: 250 }]);
  const release = Promise.withResolvers<void>(); const settled = Promise.withResolvers<void>();
  let entered = false;
  try {
    const owner = ctx.runOwner;
    const run = await owner.start(value.runId, value.runId); run.beginMeasurement();
    const stages = hooks(run, value.directory, []);
    const incomplete = await run.finish({ ...stages, captureLastState: async () => {
      entered = true;
      try {
        await release.promise;
        await writeFile(value.resourcePath, 'writer completed after enclosing disposal');
        const path = join(value.directory, 'enclosing-disposal-late.json');
        await writeFile(path, 'retained late observation');
        return [await referenceFile(path)];
      } finally { settled.resolve(); }
    } });
    assert.equal(incomplete.status, 'incomplete');
    const snapshot = structuredClone(incomplete);
    await ctx.fiber.dispose();
    await access(value.resourcePath);
    assert.ok(run.resources.pending().every(item => !item.attempted && !item.released && /unsettled/.test(item.cleanupError ?? '')));
    assert.ok(run.errors.some(error => /cleanup refused/.test(error)));
    let exported = false;
    const blocked = await run.retryExport(async () => { exported = true; return []; });
    assert.equal(blocked.status, 'incomplete'); assert.equal(exported, false);
    await assert.rejects(owner.start(value.runId, value.runId), /already owned/);
    release.resolve(); await settled.promise; await nextTurn();
    assert.equal(await readFile(value.resourcePath, 'utf8'), 'writer completed after enclosing disposal');
    assert.deepEqual(incomplete, snapshot);
    const recovered = await run.retryExport(stages.exportEvidence);
    assert.equal(recovered.status, 'error');
    assert.ok(recovered.resourceOutcomes.every(item => !item.attempted && !item.released && /cleanup refused/.test(item.cleanupError ?? '')));
    await access(value.resourcePath);
    await assert.rejects(owner.start(value.runId, value.runId), /already owned/);
  } finally {
    release.resolve(); if (entered) await settled.promise;
    await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true });
  }
});

test('cooperative abort preserves its distinct native rejection as well as the timeout reason', async () => {
  const value = await fixture(); const ctx = await host([{ ...value.descriptor, deadlineMs: 250 }]);
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const stages = hooks(run, value.directory, []);
    const completion = await run.finish({ ...stages, drainRecorders: async signal => {
      return await new Promise<readonly import('../src/plugins/application-lifecycle/index.js').ArtifactRef[]>((_, reject) => {
        signal.addEventListener('abort', () => reject(new Error('native recorder cancellation failed')), { once: true });
      });
    } });
    assert.equal(completion.status, 'error');
    assert.ok(completion.errors.includes('lifecycle deadline exceeded'));
    assert.ok(completion.errors.some(error => /native recorder cancellation failed/.test(error)));
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});


test('enclosing disposal cannot bypass a settled failed export and erase retained evidence', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const stages = hooks(run, value.directory, []);
    const incomplete = await run.finish({ ...stages, exportEvidence: async () => { throw new Error('export unavailable'); } });
    assert.equal(incomplete.status, 'incomplete');
    await ctx.fiber.dispose();
    await access(value.resourcePath);
    assert.ok(run.resources.pending().every(item => !item.attempted && !item.released && /before retained evidence export/.test(item.cleanupError ?? '')));
    assert.ok(run.errors.some(error => /cleanup refused before/.test(error)));
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});
