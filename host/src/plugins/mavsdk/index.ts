import { Service } from 'cordis';
import type { Context } from 'cordis';
import * as grpc from '@grpc/grpc-js';
import { loadSync } from '@grpc/proto-loader';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import type { ProtoGrpcType as CoreProto } from '../../generated/mavsdk/core.js';
import type { ProtoGrpcType as ActionProto } from '../../generated/mavsdk/action.js';
import type { ProtoGrpcType as TelemetryProto } from '../../generated/mavsdk/telemetry.js';
import type { CoreServiceClient } from '../../generated/mavsdk/mavsdk/rpc/core/CoreService.js';
import type { ActionServiceClient } from '../../generated/mavsdk/mavsdk/rpc/action/ActionService.js';
import type { TelemetryServiceClient } from '../../generated/mavsdk/mavsdk/rpc/telemetry/TelemetryService.js';
import type { ConnectionStateResponse__Output } from '../../generated/mavsdk/mavsdk/rpc/core/ConnectionStateResponse.js';
import type { HealthResponse__Output } from '../../generated/mavsdk/mavsdk/rpc/telemetry/HealthResponse.js';
import { within, lifecycleDeadline } from '../application-lifecycle/index.js';

export const MAVSDK_PROTO_COMMIT = '5c81ecfeb6110cf74ba75ae50b78a1b265c05670';
export const PROTO_LOADER_OPTIONS = { keepCase: true, longs: String, enums: String, defaults: true, oneofs: true } as const;
const protoRoot = fileURLToPath(new URL('../../../../proto/', import.meta.url));
export function loadMavsdkProto() {
  const definitions = loadSync([join(protoRoot, 'core/core.proto'), join(protoRoot, 'action/action.proto'), join(protoRoot, 'telemetry/telemetry.proto')],
    { ...PROTO_LOADER_OPTIONS, includeDirs: [protoRoot] });
  return grpc.loadPackageDefinition(definitions) as unknown as CoreProto & ActionProto & TelemetryProto;
}
export interface MavsdkConfig { endpoint: string; deadlineMs?: number; credentials?: grpc.ChannelCredentials; channelOptions?: grpc.ChannelOptions; }
declare module 'cordis' { interface Context { mavsdk: Mavsdk; } }

/** Native generated clients; transport readiness never asserts vehicle, health or command success. */
export class Mavsdk extends Service {
  readonly clients: { core: CoreServiceClient; action: ActionServiceClient; telemetry: TelemetryServiceClient };
  readonly deadlineMs: number;
  transportReady = false;
  private readonly streams = new Set<grpc.ClientReadableStream<unknown>>();
  constructor(ctx: Context, config: MavsdkConfig) {
    if (!config?.endpoint?.trim()) throw new TypeError('configured MAVSDK endpoint is required');
    const deadline = lifecycleDeadline(config.deadlineMs ?? 5000);
    super(ctx, 'mavsdk');
    this.deadlineMs = deadline;
    const proto = loadMavsdkProto();
    const channelOptions: grpc.ChannelOptions = { "grpc.use_local_subchannel_pool": 1, "grpc.enable_http_proxy": 0, ...config.channelOptions };
    const credentials = config.credentials ?? grpc.credentials.createInsecure();
    this.clients = {
      core: new proto.mavsdk.rpc.core.CoreService(config.endpoint, credentials, channelOptions),
      action: new proto.mavsdk.rpc.action.ActionService(config.endpoint, credentials, channelOptions),
      telemetry: new proto.mavsdk.rpc.telemetry.TelemetryService(config.endpoint, credentials, channelOptions),
    };
  }
  async *[Service.init]() {
    yield () => {
      this.transportReady = false;
      for (const stream of this.streams) stream.cancel();
      this.streams.clear();
      for (const client of Object.values(this.clients)) client.close();
    };
    await new Promise<void>((resolve, reject) => this.clients.core.waitForReady(Date.now() + this.deadlineMs,
      error => error ? reject(error) : resolve()));
    this.transportReady = true;
  }
  first<T>(stream: grpc.ClientReadableStream<T>, signal?: AbortSignal): Promise<T> {
    this.streams.add(stream as grpc.ClientReadableStream<unknown>);
    stream.on('error', () => {});
    return within(cancel => new Promise<T>((resolve, reject) => {
      const stop = () => { stream.cancel(); reject(cancel.reason ?? new Error('native stream canceled')); };
      const clean = () => { cancel.removeEventListener('abort', stop); this.streams.delete(stream as grpc.ClientReadableStream<unknown>); };
      stream.once('data', (value: T) => { clean(); stream.cancel(); resolve(value); });
      // Keep the native error listener through cancellation so CANCELLED is never unhandled.
      stream.on('error', error => { clean(); reject(error); });
      stream.once('end', () => { clean(); reject(new Error('native stream ended without an observation')); });
      cancel.addEventListener('abort', stop, { once: true });
      if (cancel.aborted) stop();
    }), this.deadlineMs, signal).finally(() => { stream.cancel(); this.streams.delete(stream as grpc.ClientReadableStream<unknown>); });
  }
  observeConnectionState(signal?: AbortSignal): Promise<ConnectionStateResponse__Output> {
    return this.first(this.clients.core.subscribeConnectionState({}, { deadline: Date.now() + this.deadlineMs }), signal);
  }
  observeHealth(signal?: AbortSignal): Promise<HealthResponse__Output> {
    return this.first(this.clients.telemetry.subscribeHealth({}, { deadline: Date.now() + this.deadlineMs }), signal);
  }
}
export default Mavsdk;
