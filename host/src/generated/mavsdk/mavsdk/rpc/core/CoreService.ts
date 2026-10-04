// Original file: proto/core/core.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { ConnectionStateResponse as _mavsdk_rpc_core_ConnectionStateResponse, ConnectionStateResponse__Output as _mavsdk_rpc_core_ConnectionStateResponse__Output } from '../../../mavsdk/rpc/core/ConnectionStateResponse.js';
import type { FeedHeartbeatWatchdogRequest as _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, FeedHeartbeatWatchdogRequest__Output as _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest__Output } from '../../../mavsdk/rpc/core/FeedHeartbeatWatchdogRequest.js';
import type { FeedHeartbeatWatchdogResponse as _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse, FeedHeartbeatWatchdogResponse__Output as _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output } from '../../../mavsdk/rpc/core/FeedHeartbeatWatchdogResponse.js';
import type { SetHeartbeatWatchdogTimeoutRequest as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, SetHeartbeatWatchdogTimeoutRequest__Output as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest__Output } from '../../../mavsdk/rpc/core/SetHeartbeatWatchdogTimeoutRequest.js';
import type { SetHeartbeatWatchdogTimeoutResponse as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse, SetHeartbeatWatchdogTimeoutResponse__Output as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output } from '../../../mavsdk/rpc/core/SetHeartbeatWatchdogTimeoutResponse.js';
import type { SetMavlinkTimeoutRequest as _mavsdk_rpc_core_SetMavlinkTimeoutRequest, SetMavlinkTimeoutRequest__Output as _mavsdk_rpc_core_SetMavlinkTimeoutRequest__Output } from '../../../mavsdk/rpc/core/SetMavlinkTimeoutRequest.js';
import type { SetMavlinkTimeoutResponse as _mavsdk_rpc_core_SetMavlinkTimeoutResponse, SetMavlinkTimeoutResponse__Output as _mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output } from '../../../mavsdk/rpc/core/SetMavlinkTimeoutResponse.js';
import type { SubscribeConnectionStateRequest as _mavsdk_rpc_core_SubscribeConnectionStateRequest, SubscribeConnectionStateRequest__Output as _mavsdk_rpc_core_SubscribeConnectionStateRequest__Output } from '../../../mavsdk/rpc/core/SubscribeConnectionStateRequest.js';

export interface CoreServiceClient extends grpc.Client {
  FeedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  FeedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  FeedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  FeedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  feedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  feedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  feedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  feedHeartbeatWatchdog(argument: _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, callback: grpc.requestCallback<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>): grpc.ClientUnaryCall;
  
  SetHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  SetHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  SetHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  SetHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setHeartbeatWatchdogTimeout(argument: _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, callback: grpc.requestCallback<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>): grpc.ClientUnaryCall;
  
  SetMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  SetMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  SetMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  SetMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  setMavlinkTimeout(argument: _mavsdk_rpc_core_SetMavlinkTimeoutRequest, callback: grpc.requestCallback<_mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>): grpc.ClientUnaryCall;
  
  SubscribeConnectionState(argument: _mavsdk_rpc_core_SubscribeConnectionStateRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_core_ConnectionStateResponse__Output>;
  SubscribeConnectionState(argument: _mavsdk_rpc_core_SubscribeConnectionStateRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_core_ConnectionStateResponse__Output>;
  subscribeConnectionState(argument: _mavsdk_rpc_core_SubscribeConnectionStateRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_core_ConnectionStateResponse__Output>;
  subscribeConnectionState(argument: _mavsdk_rpc_core_SubscribeConnectionStateRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_core_ConnectionStateResponse__Output>;
  
}

export interface CoreServiceHandlers extends grpc.UntypedServiceImplementation {
  FeedHeartbeatWatchdog: grpc.handleUnaryCall<_mavsdk_rpc_core_FeedHeartbeatWatchdogRequest__Output, _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse>;
  
  SetHeartbeatWatchdogTimeout: grpc.handleUnaryCall<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest__Output, _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse>;
  
  SetMavlinkTimeout: grpc.handleUnaryCall<_mavsdk_rpc_core_SetMavlinkTimeoutRequest__Output, _mavsdk_rpc_core_SetMavlinkTimeoutResponse>;
  
  SubscribeConnectionState: grpc.handleServerStreamingCall<_mavsdk_rpc_core_SubscribeConnectionStateRequest__Output, _mavsdk_rpc_core_ConnectionStateResponse>;
  
}

export interface CoreServiceDefinition extends grpc.ServiceDefinition {
  FeedHeartbeatWatchdog: MethodDefinition<_mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse, _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest__Output, _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>
  SetHeartbeatWatchdogTimeout: MethodDefinition<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse, _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest__Output, _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>
  SetMavlinkTimeout: MethodDefinition<_mavsdk_rpc_core_SetMavlinkTimeoutRequest, _mavsdk_rpc_core_SetMavlinkTimeoutResponse, _mavsdk_rpc_core_SetMavlinkTimeoutRequest__Output, _mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>
  SubscribeConnectionState: MethodDefinition<_mavsdk_rpc_core_SubscribeConnectionStateRequest, _mavsdk_rpc_core_ConnectionStateResponse, _mavsdk_rpc_core_SubscribeConnectionStateRequest__Output, _mavsdk_rpc_core_ConnectionStateResponse__Output>
}
