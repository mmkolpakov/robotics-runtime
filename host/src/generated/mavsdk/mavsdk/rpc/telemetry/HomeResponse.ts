// Original file: proto/telemetry/telemetry.proto

import type { HomePosition as _mavsdk_rpc_telemetry_HomePosition, HomePosition__Output as _mavsdk_rpc_telemetry_HomePosition__Output } from '../../../mavsdk/rpc/telemetry/HomePosition.js';

export interface HomeResponse {
  'home'?: (_mavsdk_rpc_telemetry_HomePosition | null);
}

export interface HomeResponse__Output {
  'home': (_mavsdk_rpc_telemetry_HomePosition__Output | null);
}
