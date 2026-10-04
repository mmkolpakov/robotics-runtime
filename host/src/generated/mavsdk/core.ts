import type * as grpc from '@grpc/grpc-js';
import type { MessageTypeDefinition } from '@grpc/proto-loader';

import type { ConnectionState as _mavsdk_rpc_core_ConnectionState, ConnectionState__Output as _mavsdk_rpc_core_ConnectionState__Output } from './mavsdk/rpc/core/ConnectionState.js';
import type { ConnectionStateResponse as _mavsdk_rpc_core_ConnectionStateResponse, ConnectionStateResponse__Output as _mavsdk_rpc_core_ConnectionStateResponse__Output } from './mavsdk/rpc/core/ConnectionStateResponse.js';
import type { CoreServiceClient as _mavsdk_rpc_core_CoreServiceClient, CoreServiceDefinition as _mavsdk_rpc_core_CoreServiceDefinition } from './mavsdk/rpc/core/CoreService.js';
import type { FeedHeartbeatWatchdogRequest as _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, FeedHeartbeatWatchdogRequest__Output as _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest__Output } from './mavsdk/rpc/core/FeedHeartbeatWatchdogRequest.js';
import type { FeedHeartbeatWatchdogResponse as _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse, FeedHeartbeatWatchdogResponse__Output as _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output } from './mavsdk/rpc/core/FeedHeartbeatWatchdogResponse.js';
import type { SetHeartbeatWatchdogTimeoutRequest as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, SetHeartbeatWatchdogTimeoutRequest__Output as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest__Output } from './mavsdk/rpc/core/SetHeartbeatWatchdogTimeoutRequest.js';
import type { SetHeartbeatWatchdogTimeoutResponse as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse, SetHeartbeatWatchdogTimeoutResponse__Output as _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output } from './mavsdk/rpc/core/SetHeartbeatWatchdogTimeoutResponse.js';
import type { SetMavlinkTimeoutRequest as _mavsdk_rpc_core_SetMavlinkTimeoutRequest, SetMavlinkTimeoutRequest__Output as _mavsdk_rpc_core_SetMavlinkTimeoutRequest__Output } from './mavsdk/rpc/core/SetMavlinkTimeoutRequest.js';
import type { SetMavlinkTimeoutResponse as _mavsdk_rpc_core_SetMavlinkTimeoutResponse, SetMavlinkTimeoutResponse__Output as _mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output } from './mavsdk/rpc/core/SetMavlinkTimeoutResponse.js';
import type { SubscribeConnectionStateRequest as _mavsdk_rpc_core_SubscribeConnectionStateRequest, SubscribeConnectionStateRequest__Output as _mavsdk_rpc_core_SubscribeConnectionStateRequest__Output } from './mavsdk/rpc/core/SubscribeConnectionStateRequest.js';

type SubtypeConstructor<Constructor extends new (...args: any) => any, Subtype> = {
  new(...args: ConstructorParameters<Constructor>): Subtype;
};

export interface ProtoGrpcType {
  mavsdk: {
    rpc: {
      core: {
        ConnectionState: MessageTypeDefinition<_mavsdk_rpc_core_ConnectionState, _mavsdk_rpc_core_ConnectionState__Output>
        ConnectionStateResponse: MessageTypeDefinition<_mavsdk_rpc_core_ConnectionStateResponse, _mavsdk_rpc_core_ConnectionStateResponse__Output>
        CoreService: SubtypeConstructor<typeof grpc.Client, _mavsdk_rpc_core_CoreServiceClient> & { service: _mavsdk_rpc_core_CoreServiceDefinition }
        FeedHeartbeatWatchdogRequest: MessageTypeDefinition<_mavsdk_rpc_core_FeedHeartbeatWatchdogRequest, _mavsdk_rpc_core_FeedHeartbeatWatchdogRequest__Output>
        FeedHeartbeatWatchdogResponse: MessageTypeDefinition<_mavsdk_rpc_core_FeedHeartbeatWatchdogResponse, _mavsdk_rpc_core_FeedHeartbeatWatchdogResponse__Output>
        SetHeartbeatWatchdogTimeoutRequest: MessageTypeDefinition<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest, _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutRequest__Output>
        SetHeartbeatWatchdogTimeoutResponse: MessageTypeDefinition<_mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse, _mavsdk_rpc_core_SetHeartbeatWatchdogTimeoutResponse__Output>
        SetMavlinkTimeoutRequest: MessageTypeDefinition<_mavsdk_rpc_core_SetMavlinkTimeoutRequest, _mavsdk_rpc_core_SetMavlinkTimeoutRequest__Output>
        SetMavlinkTimeoutResponse: MessageTypeDefinition<_mavsdk_rpc_core_SetMavlinkTimeoutResponse, _mavsdk_rpc_core_SetMavlinkTimeoutResponse__Output>
        SubscribeConnectionStateRequest: MessageTypeDefinition<_mavsdk_rpc_core_SubscribeConnectionStateRequest, _mavsdk_rpc_core_SubscribeConnectionStateRequest__Output>
      }
    }
  }
}

