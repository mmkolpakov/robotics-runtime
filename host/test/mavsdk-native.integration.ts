import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Context, FiberState } from 'cordis';
import { createServer, createConnection } from 'node:net';
import { createSocket } from 'node:dgram';
import { resolve, join } from 'node:path';
import { readFile, writeFile, mkdir, copyFile, mkdtemp, rm } from 'node:fs/promises';
import { homedir, tmpdir, userInfo } from 'node:os';
import { createHash, randomUUID } from 'node:crypto';
import { setTimeout as pause } from 'node:timers/promises';
import { Jobs } from '../src/plugins/jobs/index.js';
import { Mavsdk } from '../src/plugins/mavsdk/index.js';
async function tcpPort(): Promise<number> {
  const listener = createServer(); await new Promise<void>(done => listener.listen(0, '127.0.0.1', done));
  const address = listener.address(); assert.ok(address && typeof address !== 'string');
  await new Promise<void>((done, reject) => listener.close(error => error ? reject(error) : done())); return address.port;
}
async function udpPort(): Promise<number> {
  const socket = createSocket('udp4'); await new Promise<void>(done => socket.bind(0, '127.0.0.1', done));
  const port = socket.address().port; socket.close(); return port;
}
async function listening(port: number): Promise<boolean> {
  return new Promise(resolve => {
    const socket = createConnection({ host: '127.0.0.1', port });
    const done = (ready: boolean) => { socket.destroy(); resolve(ready); };
    socket.setTimeout(80, () => done(false)); socket.once('error', () => done(false)); socket.once('connect', () => done(true));
  });
}
test('native MAVSDK discovery uses only upstream heartbeat codec and preserves qualification boundaries', { timeout: 25000 }, async () => {
  const binary = process.env.RR_MAVSDK_SERVER ?? resolve('.tools/mavsdk_server');
  const identity = JSON.parse(await readFile('tools/mavsdk-server.v4.0.3.json', 'utf8')) as { sha256: string; size_bytes: number };
  const raw = await readFile(binary); assert.equal(raw.length, identity.size_bytes);
  assert.equal(createHash('sha256').update(raw).digest('hex'), identity.sha256);
  const grpcPort = await tcpPort(); const mavlinkPort = await udpPort();
  const directory = await mkdtemp(join(tmpdir(), 'rr-mavsdk-'));
  const ctx = new Context(); await ctx.plugin(Jobs, { timeoutMs: 22000, killTimeoutMs: 1000 });
  const abort = new AbortController();
  const native = ctx.jobs.run({ executable: binary, args: ['-p', String(grpcPort), 'udpin://127.0.0.1:' + mavlinkPort], cancelSignal: abort.signal });
  const heartbeat = ctx.jobs.run({ executable: '/usr/bin/podman', args: ['run', '--rm', '--network=host', '--name', 'rr-heartbeat-' + randomUUID(),
    '--init', '--init-path', resolve('.tools/tini'), '--userns=keep-id:uid=1000,gid=1000', '--user', '1000:1000',
    '-v', resolve('.') + ':/workspace:ro', '-v', directory + ':/run/robotics', '-w', '/workspace',
    '--entrypoint', '/workspace/.tools/mavlink/bin/python', 'localhost/rr-c-media:c12-locked',
    '/workspace/test/producers/mavlink_heartbeat.py', '--endpoint', 'udpout:127.0.0.1:' + mavlinkPort,
    '--seconds', '4', '--report', '/run/robotics/heartbeat.json'], cancelSignal: abort.signal,
    env: { PATH: '/usr/local/bin:/usr/bin:/bin', HOME: homedir(), USER: userInfo().username, LOGNAME: userInfo().username, DBUS_SESSION_BUS_ADDRESS: 'unix:path=/run/user/' + process.getuid!() + '/bus', XDG_RUNTIME_DIR: '/run/user/' + process.getuid!() } });
  let fiber: ReturnType<Context['plugin']> | undefined;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 80; attempt++) { if (await listening(grpcPort)) { ready = true; break; } await pause(50); }
    assert.equal(ready, true, 'native SDK does not start gRPC until a real codec heartbeat is discovered');
    fiber = ctx.plugin(Mavsdk, { endpoint: '127.0.0.1:' + grpcPort, deadlineMs: 5000 });
    await fiber.await(); assert.equal(fiber.state, FiberState.ACTIVE); assert.equal(ctx.mavsdk.transportReady, true);
    const connection = await ctx.mavsdk.observeConnectionState();
    assert.equal(connection.connection_state?.is_connected, true);
    const health = await ctx.mavsdk.observeHealth().catch(() => undefined);
    if (health) { assert.equal(health.health?.is_global_position_ok, false); assert.equal(health.health?.is_home_position_ok, false); }
    const sent = await heartbeat; assert.equal(sent.ok, true, sent.stderr);
    const facts = JSON.parse(await readFile(join(directory, 'heartbeat.json'), 'utf8')) as { pymavlink_version: string; codec_sha256: string; heartbeat_count: number; scope: string };
    assert.equal(facts.pymavlink_version, '2.4.50'); assert.match(facts.codec_sha256, /^[a-f0-9]{64}$/);
    assert.ok(facts.heartbeat_count > 0); assert.match(facts.scope, /no health, control or flight qualification/);
    await pause(3500);
    const disconnected = await ctx.mavsdk.observeConnectionState();
    assert.equal(disconnected.connection_state?.is_connected, false);
    const artifacts = resolve('../artifacts/host/c12');
    await mkdir(artifacts, { recursive: true });
    await copyFile(join(directory, 'heartbeat.json'), join(artifacts, 'heartbeat.json'));
    await writeFile(join(artifacts, 'mavsdk-observations.json'), JSON.stringify({ connection, disconnected, health_qualified: false, flight_qualified: false }));
    console.log(JSON.stringify({ disconnected, server_sha256: identity.sha256, connection, heartbeat: facts, health_qualified: false, flight_qualified: false }));
  } finally {
    await fiber?.dispose(); abort.abort(); const result = await native;
    assert.equal(result.canceled, true); assert.equal(await listening(grpcPort), false); assert.match(result.stdout + result.stderr, /MAVSDK version: v4.0.3/);
    await heartbeat; await ctx.fiber.dispose(); await rm(directory, { recursive: true, force: true });
  }
});
