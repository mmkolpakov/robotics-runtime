import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, rm } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { Jobs } from '../src/plugins/jobs/index.js';
import { Documents } from '../src/plugins/documents/index.js';
import { referenceFile } from '../src/plugins/application-lifecycle/index.js';
import { compositionObservation, HOST_EXTENSION_SCHEMA_URI } from '../src/plugins/application-lifecycle/composition.js';
import { fixture, host, hooks } from './lifecycle-support.js';
const root = resolve('..');
const contracts = process.env.RR_CONTRACTS_COMMAND ?? join(root, '.venv/bin/robotics-contracts');
const python = process.env.RR_PYTHON_COMMAND ?? join(root, '.venv/bin/python');
const schema = join(root, 'host/schemas/host-composition.v1.schema.json');
const template = join(root, 'packages/contracts/consumer-examples/flight-controller/qualification-profile.json');

test('host extension uses existing generic role, verifies actual refs and rejects schema/ref/shape tamper', async () => {
  const value = await fixture(); const ctx = await host([value.descriptor]);
  await ctx.plugin(Jobs); await ctx.plugin(Documents, { executable: contracts });
  try {
    const run = await ctx.runOwner.start(value.runId, value.runId); run.beginMeasurement();
    const completion = await run.finish(hooks(run, value.directory, []));
    assert.equal(completion.status, 'passed');
    const readyRef = await referenceFile(value.readyPath);
    const cleanupRef = await referenceFile(value.cleanupPath);
    const configRef = await referenceFile(value.profilePath);
    const hostIdentity = { package: '@robotics-runtime/host', version: '0.1.0-rc.0', node: process.version,
      package_lock_ref: await referenceFile(join(root, 'host/package-lock.json')) };
    const providers = [{
      id: 'finite-file-fixture', identity: { package: 'fixture', version: '1', config_ref: configRef },
      bindings: [{ service: 'backend', provider: 'finite-file-fixture', evidence_ref: readyRef }],
      capabilities: { declared: ['finite-file-lifecycle'], effective: ['finite-file-lifecycle'], qualification_refs: [cleanupRef] },
      endpoints: [{ kind: 'local-file', evidence_ref: readyRef }],
      time: [{ authority: 'fixture-observer', domain: 'wall-observation', epoch: value.runId, native_unit: 'seconds',
        precision: { representation: 'float64' as const, description: 'native float seconds retained as raw evidence; no integer ns conversion' },
        native_observation_ref: readyRef, coordinates: { frame: 'filesystem', units: 'bytes', axes: 'none' } }],
      lifecycle_refs: completion.evidenceRefs, cleanup_refs: [cleanupRef],
    }];
    const composition = compositionObservation(run, completion, hostIdentity, configRef, providers);
    const sidecar = join(value.directory, 'composition.json');
    await writeFile(sidecar, JSON.stringify(composition));
    const document = join(value.directory, 'qualification-profile.json');
    const produced = await ctx.jobs.run({ executable: python, args: [join(root, 'host/producers/attach_composition.py'),
      '--template', template, '--composition', sidecar, '--schema', schema, '--output', document] });
    assert.equal(produced.ok, true, produced.stderr);
    const checked = await ctx.documents.validate([document], { extensionSchemas: [{ uri: HOST_EXTENSION_SCHEMA_URI, path: schema }] });
    assert.equal(checked.ok, true, checked.stderr);
    const conformance = join(value.directory, 'conformance-result.json');
    const producedConformance = await ctx.jobs.run({ executable: python, args: [join(root, 'host/producers/attach_composition.py'),
      '--template', join(root, 'packages/contracts/tests/fixtures/qualification/inference/provider-conformance.json'),
      '--composition', sidecar, '--schema', schema, '--output', conformance] });
    assert.equal(producedConformance.ok, true, producedConformance.stderr);
    assert.equal((await ctx.documents.validate([conformance], { extensionSchemas: [{ uri: HOST_EXTENSION_SCHEMA_URI, path: schema }] })).ok, true);
    const undeclared = await ctx.documents.validate([document]);
    assert.equal(undeclared.ok, false); assert.match(undeclared.stderr, /extension/);
    const tamperedSchema = join(value.directory, 'schema.json'); await writeFile(tamperedSchema, Buffer.concat([await readFile(schema), Buffer.from(' ')]));
    assert.equal((await ctx.documents.validate([document], { extensionSchemas: [{ uri: HOST_EXTENSION_SCHEMA_URI, path: tamperedSchema }] })).ok, false);
    assert.throws(() => compositionObservation(run, completion, hostIdentity, configRef,
      [{ ...providers[0]!, capabilities: { declared: [], effective: ['unqualified'], qualification_refs: [] } }]), /not declared/);
    await writeFile(value.readyPath, '{}');
    const changedRef = await ctx.jobs.run({ executable: python, args: [join(root, 'host/producers/attach_composition.py'),
      '--template', template, '--composition', sidecar, '--schema', schema, '--output', join(value.directory, 'wrong-ref.json')] });
    assert.equal(changedRef.ok, false); assert.match(changedRef.stderr, /retained bytes/);
    const wrongShape = { ...composition, providers: [{ ...providers[0]!, invented_step_rpc: true }] };
    await writeFile(sidecar, JSON.stringify(wrongShape));
    // Restore exact observed bytes for the schema-form negative case.
    await writeFile(value.readyPath, JSON.stringify({ present: true, native_seconds: 0.001, representation: 'float64' }));
    const bad = await ctx.jobs.run({ executable: python, args: [join(root, 'host/producers/attach_composition.py'),
      '--template', template, '--composition', sidecar, '--schema', schema, '--output', join(value.directory, 'wrong-shape.json')] });
    assert.equal(bad.ok, false); assert.match(bad.stderr, /Additional properties|invented_step_rpc/);
  } finally { await ctx.fiber.dispose(); await rm(value.directory, { recursive: true, force: true }); }
});
