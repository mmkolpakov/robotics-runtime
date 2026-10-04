import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Context, FiberState } from 'cordis';
import * as grpc from '@grpc/grpc-js';
import { Mavsdk, loadMavsdkProto } from '../src/plugins/mavsdk/index.js';
import type { CoreServiceHandlers } from '../src/generated/mavsdk/mavsdk/rpc/core/CoreService.js';
import type { TelemetryServiceHandlers } from '../src/generated/mavsdk/mavsdk/rpc/telemetry/TelemetryService.js';
import type { ActionServiceHandlers } from '../src/generated/mavsdk/mavsdk/rpc/action/ActionService.js';
import type { ArmResponse__Output } from '../src/generated/mavsdk/mavsdk/rpc/action/ArmResponse.js';

test('official protobuf channel separates transport, disconnected device, health and rejected operation', { timeout: 5000 }, async () => {
  const proto = loadMavsdkProto(); const server = new grpc.Server();
  const calls: grpc.ServerWritableStream<unknown, unknown>[] = [];
  const track = (call: grpc.ServerWritableStream<unknown, unknown>) => { calls.push(call); call.on('error', () => {}); };
  const core: Pick<CoreServiceHandlers, 'SubscribeConnectionState'> = {
    SubscribeConnectionState: call => { track(call); call.write({ connection_state: { is_connected: false } }); },
  };
  const telemetry: Pick<TelemetryServiceHandlers, 'SubscribeHealth' | 'SubscribeUnixEpochTime' | 'SubscribePosition'> = {
    SubscribeHealth: call => { track(call); call.write({ health: { is_global_position_ok: false, is_home_position_ok: false } }); },
    SubscribeUnixEpochTime: call => { track(call); call.write({ time_us: '9007199254740993' }); },
    SubscribePosition: call => { track(call); },
  };
  const action: Pick<ActionServiceHandlers, 'Arm'> = {
    Arm: (_call, done) => done(null, { action_result: { result: 'RESULT_NO_SYSTEM', result_str: 'disconnected fixture' } }),
  };
  server.addService(proto.mavsdk.rpc.core.CoreService.service, core);
  server.addService(proto.mavsdk.rpc.telemetry.TelemetryService.service, telemetry);
  server.addService(proto.mavsdk.rpc.action.ActionService.service, action);
  const port = await new Promise<number>((resolve, reject) => server.bindAsync('127.0.0.1:0', grpc.ServerCredentials.createInsecure(), (error, bound) => error ? reject(error) : resolve(bound)));
  const ctx = new Context(); const fiber = ctx.plugin(Mavsdk, { endpoint: '127.0.0.1:' + port, deadlineMs: 100 });
  try {
    await fiber.await(); const service = ctx.mavsdk; assert.equal(fiber.state, FiberState.ACTIVE); assert.equal(ctx.mavsdk.transportReady, true);
    const connected = await ctx.mavsdk.observeConnectionState();
    assert.equal(connected.connection_state?.is_connected, false);
    const health = await ctx.mavsdk.observeHealth();
    assert.equal(health.health?.is_global_position_ok, false);
    const epoch = await ctx.mavsdk.first(ctx.mavsdk.clients.telemetry.subscribeUnixEpochTime({}));
    assert.equal(epoch.time_us, '9007199254740993'); assert.equal(typeof epoch.time_us, 'string');
    const refused = await new Promise<ArmResponse__Output>((resolve, reject) => ctx.mavsdk.clients.action.arm({}, { deadline: Date.now() + 500 }, (error, response) => error ? reject(error) : response ? resolve(response) : reject(new Error('missing native response'))));
    assert.equal(refused.action_result?.result, 'RESULT_NO_SYSTEM');
    await assert.rejects(ctx.mavsdk.first(ctx.mavsdk.clients.telemetry.subscribePosition({})), /deadline|DEADLINE/i);
    const abort = new AbortController();
    const canceled = ctx.mavsdk.first(ctx.mavsdk.clients.telemetry.subscribePosition({}), abort.signal);
    abort.abort(new Error('test stream canceled')); await assert.rejects(canceled, /canceled/);
    const waiting = ctx.mavsdk.first(ctx.mavsdk.clients.telemetry.subscribePosition({}));
    const ended = assert.rejects(waiting, /CANCELLED|cancelled/);
    await fiber.dispose(); await ended;
    assert.equal(ctx.get('mavsdk'), undefined);
    assert.ok(Object.values(service.clients).every(client => client.getChannel().getConnectivityState(false) === grpc.connectivityState.SHUTDOWN));
  } finally { await fiber.dispose(); server.forceShutdown(); }
});

test('a connected non-gRPC endpoint fails waitForReady and closes native channels', async () => {
  const { createServer } = await import('node:net');
  const sockets = new Set<import('node:net').Socket>();
  const server = createServer(socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); });
  await new Promise<void>(done => server.listen(0, '127.0.0.1', done));
  const address = server.address(); assert.ok(address && typeof address !== 'string');
  const ctx = new Context(); const fiber = ctx.plugin(Mavsdk, { endpoint: '127.0.0.1:' + address.port, deadlineMs: 80 });
  await new Promise(done => setImmediate(done));
  const instance = ctx.get('mavsdk', false); assert.ok(instance);
  try {
    await assert.rejects(fiber.await(), /deadline|Failed to connect/i);
    assert.equal(fiber.state, FiberState.FAILED);
  } finally {
    await fiber.dispose();
    assert.ok(Object.values(instance.clients as { core: grpc.Client; action: grpc.Client; telemetry: grpc.Client }).every(client => client.getChannel().getConnectivityState(false) === grpc.connectivityState.SHUTDOWN));
    for (const socket of sockets) socket.destroy();
    await new Promise<void>(done => server.close(() => done()));
  }
});
