// Original file: proto/telemetry/telemetry.proto

import type { PositionNed as _mavsdk_rpc_telemetry_PositionNed, PositionNed__Output as _mavsdk_rpc_telemetry_PositionNed__Output } from '../../../mavsdk/rpc/telemetry/PositionNed.js';
import type { VelocityNed as _mavsdk_rpc_telemetry_VelocityNed, VelocityNed__Output as _mavsdk_rpc_telemetry_VelocityNed__Output } from '../../../mavsdk/rpc/telemetry/VelocityNed.js';

export interface PositionVelocityNed {
  'position'?: (_mavsdk_rpc_telemetry_PositionNed | null);
  'velocity'?: (_mavsdk_rpc_telemetry_VelocityNed | null);
}

export interface PositionVelocityNed__Output {
  'position': (_mavsdk_rpc_telemetry_PositionNed__Output | null);
  'velocity': (_mavsdk_rpc_telemetry_VelocityNed__Output | null);
}
