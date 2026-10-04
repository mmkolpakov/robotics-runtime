// Original file: proto/telemetry/telemetry.proto

import type { Wind as _mavsdk_rpc_telemetry_Wind, Wind__Output as _mavsdk_rpc_telemetry_Wind__Output } from '../../../mavsdk/rpc/telemetry/Wind.js';

export interface WindResponse {
  'wind'?: (_mavsdk_rpc_telemetry_Wind | null);
}

export interface WindResponse__Output {
  'wind': (_mavsdk_rpc_telemetry_Wind__Output | null);
}
