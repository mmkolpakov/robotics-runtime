import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { chmod, copyFile, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';

let transcriptIndex = 0;
const reportDirectory = process.env.MCP_TEST_REPORT_DIR;
async function record(name, value) {
  if (!reportDirectory) return;
  await mkdir(reportDirectory, { recursive: true });
  await writeFile(join(reportDirectory, String(++transcriptIndex).padStart(3, '0') + '-' + name + '.json'), JSON.stringify(value, null, 2) + '\n');
}

const directory = dirname(fileURLToPath(import.meta.url));
const contractsCli = process.env.MCP_TEST_CONTRACTS_CLI;
const harnessCli = process.env.MCP_TEST_HARNESS_CLI;
assert.ok(contractsCli && harnessCli, 'set MCP_TEST_CONTRACTS_CLI and MCP_TEST_HARNESS_CLI to installed public workers');
const fixtureRoot = resolve(directory, '../../packages/contracts/tests/fixtures/qualification/inference');
const profilePath = resolve(directory, '../../packages/contracts/consumer-examples/flight-controller/qualification-profile.json');

async function fixture(t, options = {}) {
  const root = await mkdtemp(join(tmpdir(), 'mcp-offline-test-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const artifacts = join(root, 'artifacts'), scratch = join(root, 'scratch');
  await mkdir(artifacts, { mode: 0o700 }); await mkdir(scratch, { mode: 0o700 });
  const entries = [];
  async function add(id, bytes) {
    const path = id + '.json';
    await writeFile(join(artifacts, path), bytes, { mode: 0o444 });
    entries.push({ id, path, sha256: createHash('sha256').update(bytes).digest('hex'), size_bytes: bytes.length });
  }
  await add('profile', await readFile(profilePath));
  await add('invalid', Buffer.from('{}'));
  for (const role of ['scenario', 'runtime', 'model', 'dataset', 'result']) await add(role, options.documents?.[role] ?? await readFile(join(fixtureRoot, role + '.json')));
  await add('metrics', Buffer.from('{"resourceMetrics":[{"scopeMetrics":[{"scope":{"name":"software-fixture"},"metrics":[{"name":"fixture.counter","sum":{"aggregationTemporality":2,"isMonotonic":true,"dataPoints":[{"asInt":"1","startTimeUnixNano":"1791450000000000000","timeUnixNano":"1791450001000000000"}]}}]}]}]}\n'));
  for (const [id, bytes] of Object.entries(options.extraArtifacts ?? {})) await add(id, bytes);
  const config = { artifactRoot: artifacts, scratchRoot: scratch, contractsCli, harnessCli,
    limits: options.limits, artifacts: entries, schemas: [{ id: 'scenario', schema: 'acceptance-scenario.v1' }],
    bundles: [{ id: 'inference', scenario: 'scenario', runtime: 'runtime', model: 'model', dataset: 'dataset' }] };
  Object.assign(config, options.config);
  const configPath = join(root, 'bootstrap.json'); await writeFile(configPath, JSON.stringify(config));
  const transport = new StdioClientTransport({ command: process.execPath,
    args: [...(options.nodeArgs ?? []), resolve(directory, '../bin/server.mjs'), '--config', configPath], stderr: 'pipe', env: {} });
  const errors = [];
  transport.stderr.on('data', bytes => errors.push(bytes.toString()));
  const client = new Client({ name: 'offline-tools-integration', version: '1.0.0' });
  t.after(async () => { await client.close(); await transport.close(); });
  try { await client.connect(transport); } catch (error) { error.message += ': ' + errors.join(''); throw error; }
  await record('initialized', { server: client.getServerVersion(), capabilities: client.getServerCapabilities(), scope: 'source offline adapter and installed public workers' });
  return { root, artifacts, scratch, entries, config, client, transport, errors, call: async (name, args = {}) => {
    const response = await client.callTool({ name, arguments: args });
    await record(name, { arguments: args, response });
    assert.equal(response.content[0].type, 'text');
    return { response, value: JSON.parse(response.content[0].text) };
  } };
}

test('official stdio client initializes, lists exactly six read tools and calls installed public workers', { timeout: 30000 }, async t => {
  const f = await fixture(t);
  const list = await f.client.listTools();
  assert.deepEqual(list.tools.map(x => x.name).sort(), [
    'describe_contract', 'explain_bundle', 'explain_result', 'inspect_offline_readiness', 'summarize_otlp', 'validate_documents',
  ]);
  assert.ok(list.tools.every(x => x.annotations.readOnlyHint && !x.annotations.destructiveHint));
  const described = await f.call('describe_contract', { schema_id: 'scenario' });
  assert.equal(described.value.exitCode, 0); assert.equal(described.response.isError, false);
  assert.match(described.value.stdout, /acceptance-scenario.v1/);
  const validated = await f.call('validate_documents', { artifact_ids: ['profile'] });
  assert.equal(validated.value.exitCode, 0); assert.equal(validated.value.ok, true);
  const explained = await f.call('explain_bundle', { bundle_id: 'inference' });
  assert.equal(explained.value.exitCode, 0, explained.value.stderr);
  assert.match(explained.value.stdout, /scenario_id/);
  const summarized = await f.call('summarize_otlp', { artifact_id: 'metrics' });
  assert.equal(summarized.value.exitCode, 0); assert.equal(JSON.parse(summarized.value.stdout).sample_count, 1);
  const result = await f.call('explain_result', { artifact_id: 'result' });
  assert.equal(result.value.exitCode, 0, result.value.stderr);
  const ready = await f.call('inspect_offline_readiness');
  assert.equal(ready.value.exitCode, 0, ready.value.stderr);
  const doctor = JSON.parse(ready.value.stdout);
  assert.equal(doctor.mode, 'offline'); assert.equal(doctor.robotics_acceptance_harness, '0.21.0');
  assert.equal(doctor.robotics_runtime_contracts, '0.20.0');
  assert.deepEqual(await readdir(f.scratch), []);
  assert.equal(f.errors.join(''), '');
});

test('public CLI input refusal preserves its actual exit, stderr and error result', async t => {
  const f = await fixture(t);
  const result = await f.call('validate_documents', { artifact_ids: ['invalid'] });
  const direct = spawnSync(contractsCli, ['--format', 'json', 'validate', join(f.artifacts, 'invalid.json')], { encoding: 'utf8' });
  assert.equal(result.value.exitCode, direct.status);
  assert.equal(result.value.ok, false); assert.equal(result.response.isError, true);
  assert.equal(result.value.timedOut, false); assert.equal(result.value.canceled, false);
  assert.equal(result.value.signal, null);
  assert.match(result.value.stdout + result.value.stderr, /schema_version|schema version/i);
});

test('64-bit worker JSON text remains exact through the MCP wire', async t => {
  const probeRoot = await mkdtemp(join(tmpdir(), 'mcp-raw-text-probe-'));
  t.after(() => rm(probeRoot, { recursive: true, force: true }));
  const probe = join(probeRoot, 'json-output');
  await writeFile(probe, '#!' + process.execPath + '\nconsole.log(\'{"observed_at_ns":9007199254740993}\');\n', { mode: 0o500 });
  const f = await fixture(t, { config: { contractsCli: probe } });
  const result = await f.call('describe_contract', { schema_id: 'scenario' });
  assert.equal(result.value.exitCode, 0, JSON.stringify(result.value));
  assert.equal(result.value.stdout, '{"observed_at_ns":9007199254740993}');
  assert.doesNotMatch(result.value.stdout, /9007199254740992/);
});

test('unregistered IDs and arbitrary path/argv fields cannot reach workers', async t => {
  const f = await fixture(t);
  const unknown = await f.call('validate_documents', { artifact_ids: ['outside'] });
  assert.equal(unknown.value.worker_started, false); assert.equal(unknown.response.isError, true);
  const extra = await f.client.callTool({ name: 'validate_documents', arguments: { artifact_ids: ['profile'], path: '/etc/passwd', argv: ['--help'] } });
  assert.equal(extra.isError, true);
  await assert.rejects(f.client.callTool({ name: 'start_run', arguments: {} }), /not found/);
  assert.deepEqual(await readdir(f.scratch), []);
});

test('changed bytes, symlinks and oversize artifacts refuse before worker startup', async t => {
  const f = await fixture(t);
  const path = join(f.artifacts, 'profile.json');
  const original = await readFile(path);
  await chmod(path, 0o600); await writeFile(path, Buffer.alloc(original.length, 32)); await chmod(path, 0o444);
  const changed = await f.call('validate_documents', { artifact_ids: ['profile'] });
  assert.equal(changed.value.worker_started, false); assert.match(changed.value.error, /digest/);
  await rm(path); await symlink(profilePath, path);
  const linked = await f.call('validate_documents', { artifact_ids: ['profile'] });
  assert.equal(linked.value.worker_started, false); assert.match(linked.value.error, /symlink/);
  assert.deepEqual(await readdir(f.scratch), []);
  const small = await fixture(t, { limits: { maxInputBytes: 1 } });
  const tooLarge = await small.call('validate_documents', { artifact_ids: ['profile'] });
  assert.equal(tooLarge.value.worker_started, false); assert.match(tooLarge.value.error, /byte limit/);
});

test('same-digest symlinked parent and outside registry path are rejected', async t => {
  const f = await fixture(t);
  await mkdir(join(f.root, 'outside'));
  await copyFile(profilePath, join(f.root, 'outside', 'profile.json'));
  await rm(f.artifacts, { recursive: true });
  await symlink(join(f.root, 'outside'), f.artifacts);
  const denied = await f.call('validate_documents', { artifact_ids: ['profile'] });
  assert.equal(denied.value.worker_started, false);
  assert.deepEqual(await readdir(f.scratch), []);
});

test('public Jobs timeout remains visible through real MCP transport', { timeout: 15000 }, async t => {
  const probeRoot = await mkdtemp(join(tmpdir(), 'mcp-worker-probe-'));
  t.after(() => rm(probeRoot, { recursive: true, force: true }));
  const probe = join(probeRoot, 'slow');
  await writeFile(probe, '#!' + process.execPath + '\nprocess.on("SIGTERM", () => {}); console.log("owned-pid:" + process.pid); setInterval(() => {}, 1000);\n', { mode: 0o500 });
  const f = await fixture(t, { limits: { timeoutMs: 300 }, config: { contractsCli: probe } });
  const result = await f.call('describe_contract', { schema_id: 'scenario' });
  assert.equal(result.value.ok, false); assert.equal(result.value.timedOut, true);
  assert.equal(result.value.canceled, false); assert.equal(result.response.isError, true);
  const pid = Number(/owned-pid:(\d+)/.exec(result.value.stdout)[1]);
  assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' });
  assert.deepEqual(await readdir(f.scratch), []);
});

test('outside relative paths refuse bootstrap before tool registration', async t => {
  const bytes = await readFile(profilePath);
  await assert.rejects(fixture(t, { config: { artifacts: [{
    id: 'outside', path: '../outside.json', size_bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
  }] } }));
});

test('public Jobs output overflow preserves refusal metadata', async t => {
  const probeRoot = await mkdtemp(join(tmpdir(), 'mcp-output-probe-'));
  t.after(() => rm(probeRoot, { recursive: true, force: true }));
  const probe = join(probeRoot, 'oversize-output');
  await writeFile(probe, '#!' + process.execPath + '\nprocess.stdout.write("x".repeat(8192));\n', { mode: 0o500 });
  const f = await fixture(t, { limits: { maxOutputBytes: 128 }, config: { contractsCli: probe } });
  const result = await f.call('describe_contract', { schema_id: 'scenario' });
  assert.equal(result.value.ok, false); assert.equal(result.response.isError, true);
  assert.match(result.value.code + result.value.diagnostic, /BUFFER|buffer/i);
  assert.equal(result.value.timedOut, false); assert.equal(result.value.canceled, false);
  assert.deepEqual(await readdir(f.scratch), []);
});

test('MCP request cancellation settles the owned read worker and removes snapshots', { timeout: 15000 }, async t => {
  const root = await mkdtemp(join(tmpdir(), 'mcp-cancel-probe-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const pidFile = join(root, 'pid'), probe = join(root, 'wait');
  const program = '#!' + process.execPath + '\nimport { writeFileSync } from "node:fs"; writeFileSync(' + JSON.stringify(pidFile)
    + ', String(process.pid)); process.on("SIGTERM", () => {}); setInterval(() => {}, 1000);\n';
  await writeFile(probe, program, { mode: 0o500 });
  const f = await fixture(t, { config: { contractsCli: probe } });
  const controller = new AbortController();
  const request = f.client.callTool({ name: 'describe_contract', arguments: { schema_id: 'scenario' } }, { signal: controller.signal });
  let pid;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { pid = Number(await readFile(pidFile, 'utf8')); break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.ok(Number.isSafeInteger(pid) && pid > 0, 'controlled worker never started');
  controller.abort(new Error('controlled client cancellation'));
  await assert.rejects(request);
  let gone = false;
  for (let attempt = 0; attempt < 200; attempt++) {
    try { process.kill(pid, 0); } catch (error) { if (error.code === 'ESRCH') { gone = true; break; } throw error; }
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.equal(gone, true);
  for (let attempt = 0; attempt < 100 && (await readdir(f.scratch)).length; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.deepEqual(await readdir(f.scratch), []);
});

test('trusted Nav2 extension registry uses actual public validation and explanation', async t => {
  const schema = await readFile(join(directory, 'fixtures/nav2.schema.json'));
  const digest = createHash('sha256').update(schema).digest('hex');
  const scenario = JSON.parse(await readFile(join(fixtureRoot, 'scenario.json'), 'utf8'));
  const namespace = 'org.example.nav2-turtlebot3', uri = 'urn:nav2-turtlebot3:scenario:v1';
  scenario.extension_schemas = [{ namespace, schema_uri: uri, sha256: digest }];
  scenario.extensions = { [namespace]: { case: 'success', goal: { x: 1, y: -0.5 },
    action_budget_sec: 120, application_timeout_sec: 2, max_final_pose_error_m: 0.35,
    min_displacement_m: 0.5, max_observation_age_sec: 2, odometry_frame: 'odom',
    required_tf_edges: [['map', 'odom']] } };
  const documents = { scenario: Buffer.from(JSON.stringify(scenario)) };
  const extension = { uri, artifact_id: 'nav2_schema' };
  const f = await fixture(t, { documents, extraArtifacts: { nav2_schema: schema },
    config: { extensionSchemas: [extension] } });
  const valid = await f.call('validate_documents', { artifact_ids: ['scenario'] });
  assert.equal(valid.value.ok, true, valid.value.stdout + valid.value.stderr);
  assert.ok(valid.value.inputRefs.some(x => x.id === 'nav2_schema' && x.sha256 === digest));
  const explained = await f.call('explain_bundle', { bundle_id: 'inference' });
  assert.equal(explained.value.ok, true, explained.value.stderr);
  const missing = await fixture(t, { documents });
  const refusal = await missing.call('validate_documents', { artifact_ids: ['scenario'] });
  assert.equal(refusal.value.ok, false); assert.match(refusal.value.stdout + refusal.value.stderr, /schema.*supplied|schema.*missing/i);
  scenario.extension_schemas[0].sha256 = 'f'.repeat(64);
  const wrong = await fixture(t, { documents: { scenario: Buffer.from(JSON.stringify(scenario)) },
    extraArtifacts: { nav2_schema: schema }, config: { extensionSchemas: [extension] } });
  const mismatch = await wrong.call('validate_documents', { artifact_ids: ['scenario'] });
  assert.equal(mismatch.value.ok, false); assert.match(mismatch.value.stdout + mismatch.value.stderr, /digest|sha256/i);
  scenario.extension_schemas[0].sha256 = digest;
  scenario.extensions[namespace].goal.x = 20;
  const invalid = await fixture(t, { documents: { scenario: Buffer.from(JSON.stringify(scenario)) },
    extraArtifacts: { nav2_schema: schema }, config: { extensionSchemas: [extension] } });
  const denied = await invalid.call('validate_documents', { artifact_ids: ['scenario'] });
  assert.equal(denied.value.ok, false); assert.match(denied.value.stdout + denied.value.stderr, /maximum|20|10/);
  const capped = await fixture(t, { documents, extraArtifacts: { nav2_schema: schema },
    limits: { maxInputBytes: documents.scenario.length }, config: { extensionSchemas: [extension] } });
  const combined = await capped.call('validate_documents', { artifact_ids: ['scenario'] });
  assert.equal(combined.value.worker_started, false); assert.match(combined.value.error, /byte limit/);
});

test('stdio close settles owned Jobs and exits naturally without a root DISPOSED claim', { timeout: 15000 }, async t => {
  const root = await mkdtemp(join(tmpdir(), 'mcp-close-control-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const pidFile = join(root, 'worker.pid'), receipt = join(root, 'server-exit.json'), started = join(root, 'server-start.json'), activeFile = join(root, 'server-active.json');
  const observer = join(root, 'observe-exit.mjs'), probe = join(root, 'worker');
  await writeFile(observer, 'import { writeFileSync } from "node:fs"; writeFileSync(' + JSON.stringify(started)
    + ', JSON.stringify({ pid: process.pid, argv: process.argv })); setTimeout(() => writeFileSync(' + JSON.stringify(activeFile)
    + ', JSON.stringify(process.getActiveResourcesInfo())), 3000).unref(); process.on("exit", code => writeFileSync('
    + JSON.stringify(receipt) + ', JSON.stringify({ code, pid: process.pid })));');
  await writeFile(probe, '#!' + process.execPath + '\nimport { writeFileSync } from "node:fs"; writeFileSync('
    + JSON.stringify(pidFile) + ', String(process.pid)); process.on("SIGTERM", () => {}); setInterval(() => {}, 1000);\n', { mode: 0o500 });
  const f = await fixture(t, { nodeArgs: ['--import', observer], config: { contractsCli: probe } });
  const serverPid = f.transport.pid;
  const request = f.client.callTool({ name: 'describe_contract', arguments: { schema_id: 'scenario' } }).catch(error => error);
  let workerPid;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { workerPid = Number(await readFile(pidFile, 'utf8')); break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.ok(Number.isSafeInteger(workerPid) && workerPid > 0);
  await f.client.close(); await f.transport.close(); await request;
  let exit;
  for (let attempt = 0; attempt < 200; attempt++) {
    try { exit = JSON.parse(await readFile(receipt, 'utf8')); break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  assert.equal(exit?.code, 0, f.errors.join('') + ' serverPid=' + serverPid + ' workerPid=' + workerPid + ' start=' + await readFile(started, 'utf8').catch(() => 'absent') + ' active=' + await readFile(activeFile, 'utf8').catch(() => 'absent'));
  assert.equal(exit.pid, serverPid);
  assert.throws(() => process.kill(serverPid, 0), { code: 'ESRCH' });
  assert.throws(() => process.kill(workerPid, 0), { code: 'ESRCH' });
  assert.deepEqual(await readdir(f.scratch), []);
  await record('stdio-close', { exit, serverPid, workerPid, worker_absent: true, snapshots_absent: true,
    scope: 'actual process/Jobs closure; root Fiber ACTIVE restart is not DISPOSED' });
});

test('public explain compares metadata without reading external file or HTTP references', async t => {
  const root = await mkdtemp(join(tmpdir(), 'mcp-external-reference-control-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const canary = join(root, 'unregistered.bin'), events = join(root, 'external-events.txt'), auditReady = join(root, 'audit-ready.txt');
  await writeFile(canary, 'unregistered canary');
  const auditDir = join(root, 'audit'); await mkdir(auditDir);
  await writeFile(join(auditDir, 'sitecustomize.py'), 'import sys, os\n'
    + 'with open(' + JSON.stringify(auditReady) + ',"w") as f: f.write("ready")\n'
    + 'canary=' + JSON.stringify(canary) + '\nevents=' + JSON.stringify(events) + '\n'
    + 'def audit(event,args):\n'
    + ' if (event=="open" and isinstance(args[0],str) and canary in args[0]) or event in ("socket.connect","urllib.Request"):\n'
    + '  with open(events,"a") as f: f.write(event+"\\n")\n'
    + '  raise RuntimeError("external reference access refused by control")\n'
    + 'sys.addaudithook(audit)\n');
  const wrapper = join(root, 'public-harness');
  const quote = value => "'" + value.replaceAll("'", "'\\''") + "'";
  await writeFile(wrapper, '#!/bin/sh\nPYTHONPATH=' + quote(auditDir) + ' exec ' + quote(harnessCli) + ' "$@"\n', { mode: 0o500 });
  const replaceUris = (value, replacement) => {
    if (typeof value === 'string') return /^(?:file|https?|s3):/.test(value) ? replacement + '?reference=' + createHash('sha256').update(value).digest('hex') : value;
    if (Array.isArray(value)) return value.map(item => replaceUris(item, replacement));
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key,item]) => [key, replaceUris(item,replacement)]));
    return value;
  };
  for (const uri of ['file://' + canary, 'http://127.0.0.1:9/unregistered']) {
    const model = replaceUris(JSON.parse(await readFile(join(fixtureRoot, 'model.json'), 'utf8')), uri);
    const dataset = replaceUris(JSON.parse(await readFile(join(fixtureRoot, 'dataset.json'), 'utf8')), uri);
    const modelBytes = Buffer.from(JSON.stringify(model)), datasetBytes = Buffer.from(JSON.stringify(dataset));
    const modelDigest = createHash('sha256').update(modelBytes).digest('hex');
    const scenario = JSON.parse(await readFile(join(fixtureRoot, 'scenario.json'), 'utf8'));
    const runtime = JSON.parse(await readFile(join(fixtureRoot, 'runtime.json'), 'utf8'));
    scenario.model_manifest_sha256 = modelDigest;
    scenario.dataset_manifest_sha256 = createHash('sha256').update(datasetBytes).digest('hex');
    runtime.workload.model.manifest_sha256 = modelDigest;
    const f = await fixture(t, { config: { harnessCli: wrapper }, documents: {
      scenario: Buffer.from(JSON.stringify(scenario)), runtime: Buffer.from(JSON.stringify(runtime)),
      model: modelBytes, dataset: datasetBytes,
    } });
    const result = await f.call('explain_bundle', { bundle_id: 'inference' });
    assert.equal(result.value.ok, true, result.value.stderr);
    assert.equal(await readFile(auditReady, 'utf8'), 'ready');
    await assert.rejects(readFile(events), { code: 'ENOENT' });
    assert.equal(await readFile(canary, 'utf8'), 'unregistered canary');
    await record('external-reference-closure', { uri, result: result.value,
      external_open_or_connect_events: 0, scope: 'actual public CLI with standard Python audit hook; no fetched asset qualification' });
  }
  const blocked = spawnSync(join(dirname(harnessCli), 'python'), ['-c', 'open(' + JSON.stringify(canary) + ').read()'],
    { env: { PATH: '/usr/bin:/bin', PYTHONPATH: auditDir, PYTHONDONTWRITEBYTECODE: '1' }, encoding: 'utf8' });
  assert.notEqual(blocked.status, 0);
  assert.match(await readFile(events, 'utf8'), /open/);
  await record('external-reference-positive-control', { exitCode: blocked.status, stderr: blocked.stderr,
    hook_loaded: true, forbidden_open_observed_and_refused: true });
});
