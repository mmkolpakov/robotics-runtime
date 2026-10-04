// Original file: proto/telemetry/telemetry.proto

import type { GpsInfo as _mavsdk_rpc_telemetry_GpsInfo, GpsInfo__Output as _mavsdk_rpc_telemetry_GpsInfo__Output } from '../../../mavsdk/rpc/telemetry/GpsInfo.js';

export interface GpsInfoResponse {
  'gps_info'?: (_mavsdk_rpc_telemetry_GpsInfo | null);
}

export interface GpsInfoResponse__Output {
  'gps_info': (_mavsdk_rpc_telemetry_GpsInfo__Output | null);
}
