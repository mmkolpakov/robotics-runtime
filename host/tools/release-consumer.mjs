import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { access, chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { setTimeout as pause } from 'node:timers/promises';
import { Context, Admission, RunOwner, RunStartupError, referenceFile } from '@robotics-runtime/host';

const payload = 'owned finite release fixture\n';
const provider = `import { access, readFile, rm, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
async function ref(path) {
  const bytes = await readFile(path);
  return { uri: pathToFileURL(path).href, sha256: createHash('sha256').update(bytes).digest('hex'), size_bytes: bytes.length };
}
export default async function provider(ctx, config) {
  await writeFile(config.resource, config.payload);
  ctx.runResources.track({ id: 'fixture', ownerId: config.ownerId,
    cleanup: () => rm(config.resource),
    verifyCleanup: async signal => {
      signal.throwIfAborted();
      let released = false;
      try { await access(config.resource); } catch (error) { if (error.code !== 'ENOENT') throw error; released = true; }
      await writeFile(config.cleanup, JSON.stringify({ released, ownerId: config.ownerId }));
      return { released, evidenceRefs: [await ref(config.cleanup)] };
    },
  });
  ctx.provide('backend', { ready: async signal => {
    signal.throwIfAborted();
    if (config.mode === 'cancel') return new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => reject(signal.reason), { once: true });
      writeFile(config.ready, 'probe entered').catch(reject);
    });
    await writeFile(config.ready, 'ready');
    return { ready: true, evidenceRefs: [await ref(config.ready)] };
  } });
}
provider.inject = ['runResources'];
`;

async function waitForProbe(path) {
  const deadline = performance.now() + 5000;
  while (performance.now() < deadline) {
    try { await access(path); return; } catch (error) { if (error.code !== 'ENOENT') throw error; }
    await pause(10);
  }
  throw new Error('installed provider did not enter its probe');
}

async function checkedBytes(path) {
  const ref = await referenceFile(path);
  const bytes = await readFile(path);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), ref.sha256);
  assert.equal(bytes.length, ref.size_bytes);
  return { ...ref, bytes_base64: bytes.toString('base64') };
}

async function exercise(mode) {
  const directory = await mkdtemp(join(tmpdir(), 'host-release-lifecycle-'));
  const ctx = new Context(), runId = randomUUID();
  const resource = join(directory, 'resource'), ready = join(directory, 'ready');
  const cleanup = join(directory, 'cleanup.json'), retained = join(directory, 'retained.bin');
  const modulePath = join(directory, 'provider.mjs'), profilePath = join(directory, 'profile.yml');
  try {
    await writeFile(modulePath, provider, { mode: 0o444 });
    await writeFile(profilePath, '- id: backend\n  name: "./provider.mjs"\n  config: ' + JSON.stringify({
      ownerId: runId, resource, ready, cleanup, payload, mode,
    }) + '\n', { mode: 0o444 });
    const files = await Promise.all([profilePath, modulePath].map(async path => ({
      path, sha256: (await referenceFile(path)).sha256,
    })));
    await ctx.plugin(Admission, { profiles: [{ id: runId, profilePath, files,
      requiredBindings: [{ entryId: 'backend', service: 'backend' }], isolatedServices: ['backend'], deadlineMs: 5000 }] });
    await ctx.plugin(RunOwner);
    let run, incomplete, expectedError;
    if (mode === 'cancel') {
      const cancel = new AbortController();
      const starting = ctx.runOwner.start(runId, runId, { cancelSignal: cancel.signal })
        .then(() => new Error('canceled startup unexpectedly succeeded'), error => error);
      await waitForProbe(ready);
      expectedError = 'installed consumer canceled startup';
      cancel.abort(new Error(expectedError));
      const failure = await starting;
      assert.ok(failure instanceof RunStartupError);
      assert.match(failure.message, /installed consumer canceled startup/);
      run = failure.run; incomplete = failure.completion;
    } else {
      run = await ctx.runOwner.start(runId, runId);
      run.beginMeasurement();
      const stage = name => async signal => {
        signal.throwIfAborted();
        const path = join(directory, name + '.json');
        await writeFile(path, JSON.stringify({ runId, stage: name }));
        return [await referenceFile(path)];
      };
      expectedError = 'installed consumer export unavailable';
      incomplete = await run.finish({ closeMeasurement: stage('close'), captureLastState: stage('capture'),
        drainRecorders: stage('drain'), exportEvidence: async () => { throw new Error(expectedError); } });
    }
    assert.equal(incomplete.status, 'incomplete');
    assert.equal(run.phase, 'retained');
    assert.equal(incomplete.resourceOutcomes.length, 1);
    assert.ok(incomplete.resourceOutcomes.every(item => !item.attempted && !item.released));
    assert.equal(await readFile(resource, 'utf8'), payload);
    await assert.rejects(access(retained), { code: 'ENOENT' });
    await assert.rejects(ctx.runOwner.start(runId, runId), /already owned/);
    const completion = await run.retryExport(async signal => {
      signal.throwIfAborted();
      const bytes = mode === 'cancel' ? Buffer.from(expectedError) : await readFile(resource);
      await writeFile(retained, bytes);
      await chmod(retained, 0o444);
      return [await referenceFile(retained)];
    });
    assert.equal(completion.status, 'error');
    assert.ok(completion.errors.some(error => error.includes(expectedError)));
    assert.equal(completion.resourceOutcomes.length, 1);
    assert.ok(completion.resourceOutcomes.every(item => item.attempted && item.released));
    await assert.rejects(access(resource), { code: 'ENOENT' });
    const evidence = await checkedBytes(retained), cleanupEvidence = await checkedBytes(cleanup);
    assert.equal(Buffer.from(evidence.bytes_base64, 'base64').toString(), mode === 'cancel' ? expectedError : payload);
    assert.deepEqual(JSON.parse(Buffer.from(cleanupEvidence.bytes_base64, 'base64').toString()), { released: true, ownerId: runId });
    assert.ok(completion.evidenceRefs.some(ref => ref.sha256 === evidence.sha256 && ref.size_bytes === evidence.size_bytes));
    assert.ok(completion.resourceOutcomes[0].evidenceRefs.some(ref => ref.sha256 === cleanupEvidence.sha256));
    return { mode, retained_before_retry: true, raw_removed_after_export: true, status: completion.status,
      errors: completion.errors, retained: evidence, cleanup: cleanupEvidence };
  } finally {
    await ctx.fiber.dispose();
    await rm(directory, { recursive: true, force: true });
  }
}

export async function verifyInstalledLifecycle() {
  return { scope: 'installed generic file lifecycle; not native provider qualification',
    cases: [await exercise('cancel'), await exercise('export-retry')] };
}
