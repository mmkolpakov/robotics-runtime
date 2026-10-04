// Original file: proto/telemetry/telemetry.proto

import type { Position as _mavsdk_rpc_telemetry_Position, Position__Output as _mavsdk_rpc_telemetry_Position__Output } from '../../../mavsdk/rpc/telemetry/Position.js';

export interface PositionResponse {
  'position'?: (_mavsdk_rpc_telemetry_Position | null);
}

export interface PositionResponse__Output {
  'position': (_mavsdk_rpc_telemetry_Position__Output | null);
}
