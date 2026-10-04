// Original file: proto/core/core.proto

import type { ConnectionState as _mavsdk_rpc_core_ConnectionState, ConnectionState__Output as _mavsdk_rpc_core_ConnectionState__Output } from '../../../mavsdk/rpc/core/ConnectionState.js';

export interface ConnectionStateResponse {
  'connection_state'?: (_mavsdk_rpc_core_ConnectionState | null);
}

export interface ConnectionStateResponse__Output {
  'connection_state': (_mavsdk_rpc_core_ConnectionState__Output | null);
}
