import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { createHash } from 'node:crypto';
import { Context } from 'cordis';
import { Jobs } from '../src/plugins/jobs/index.js';
import { Documents } from '../src/plugins/documents/index.js';
import { Evaluation } from '../src/plugins/evaluation/index.js';
const root = resolve('..');
const contracts = process.env.RR_CONTRACTS_COMMAND ?? join(root, '.venv/bin/robotics-contracts');
const acceptance = process.env.RR_ACCEPTANCE_COMMAND ?? join(root, '.venv/bin/robotics-acceptance');
const python = process.env.RR_PYTHON_COMMAND ?? join(root, '.venv/bin/python');
const hash = (raw: Uint8Array) => createHash('sha256').update(raw).digest('hex');
test('installed commands own exact files, integer ns, evaluation JSON/JUnit and diagnostics', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'rr-host-workers-'));
  const ctx = new Context();
  await ctx.plugin(Jobs, { timeoutMs: 30000, maxBufferBytes: 1048576 });
  await ctx.plugin(Documents, { executable: contracts });
  await ctx.plugin(Evaluation, { executable: acceptance });
  try {
    assert.equal((await ctx.documents.execute(['--help'])).ok, true);
    assert.equal((await ctx.evaluation.execute(['--version'])).ok, true);
    const source = join(root, 'packages/harness/tests/fixtures/simulation/runtime.yaml');
    const raw = await readFile(source);
    const validated = await ctx.documents.validate([source]);
    assert.equal(validated.ok, true, validated.stderr); assert.equal(hash(await readFile(source)), hash(raw));
    const integerTemplate = join(directory, 'runtime-template.yaml');
    await writeFile(integerTemplate, Buffer.concat([raw, Buffer.from('\nextensions:\n  org.example.raw:\n    integer_ns: 9007199254740993\n')]));
    const output = join(directory, 'runtime.json');
    const written = await ctx.documents.execute(['runtime-manifest', 'init', '--template', integerTemplate, '--output', output]);
    assert.equal(written.ok, true, written.stderr); assert.match(await readFile(output, 'utf8'), /9007199254740993/);
    const malformed = join(directory, 'malformed.json');
    await writeFile(malformed, '{"schema_version":"runtime-manifest.v1"}');
    const invalid = await ctx.documents.validate([malformed]);
    assert.equal(invalid.ok, false); assert.match(invalid.stderr, /error_id/);
    const prepared = await ctx.jobs.run({ executable: python, args: [join(root, 'host/test/producers/worker_fixture.py'), '--source-root', root, '--output', directory] });
    assert.equal(prepared.ok, true, prepared.stderr);
    const input = {
      scenario: join(root, 'packages/harness/tests/fixtures/simulation/scenario.yaml'), runtime: source,
      runId: 'run-01234567-89ab-4def-8123-456789abcdef', domainId: 'primary',
      runContext: join(directory, 'run.json'), evidenceIndex: join(directory, 'evidence.json'),
      otelMetrics: join(directory, 'metrics.ndjson'), windowStartNs: '9007199254740993',
      windowEndNs: '9007200254740993', outputDirectory: join(directory, 'result'), diagnosticOutput: join(directory, 'diagnostic.json'),
    };
    const evaluated = await ctx.evaluation.evaluate(input);
    assert.equal(evaluated.exitCode, 1, evaluated.stderr);
    const result = JSON.parse(await readFile(join(directory, 'result/acceptance-result.json'), 'utf8')) as { status: string; evaluation_mode: string; unevaluated: string[] };
    assert.notEqual(result.status, 'passed'); assert.equal(result.evaluation_mode, 'offline');
    assert.ok(result.unevaluated.includes('$.observed_ros_graph'));
    assert.match(await readFile(join(directory, 'result/junit.xml'), 'utf8'), /testsuite/);
    const broken = await ctx.evaluation.evaluate({ ...input, evidenceIndex: malformed, outputDirectory: join(directory, 'broken'), diagnosticOutput: join(directory, 'broken-diagnostic.json') });
    assert.equal(broken.ok, false); assert.match(await readFile(join(directory, 'broken-diagnostic.json'), 'utf8'), /error/);
    const limited = await ctx.evaluation.evaluate({ ...input, outputDirectory: join(directory, 'limited'), diagnosticOutput: join(directory, 'limited-diagnostic.json'), maxRawEvidenceBytes: 1 });
    assert.equal(limited.ok, false); assert.match(await readFile(join(directory, 'limited-diagnostic.json'), 'utf8'), /max_raw_evidence_bytes/);
  } finally { await ctx.fiber.dispose(); await rm(directory, { recursive: true, force: true }); }
});
