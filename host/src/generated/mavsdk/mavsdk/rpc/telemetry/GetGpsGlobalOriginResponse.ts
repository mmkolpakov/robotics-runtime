// Original file: proto/telemetry/telemetry.proto

import type { TelemetryResult as _mavsdk_rpc_telemetry_TelemetryResult, TelemetryResult__Output as _mavsdk_rpc_telemetry_TelemetryResult__Output } from '../../../mavsdk/rpc/telemetry/TelemetryResult.js';
import type { GpsGlobalOrigin as _mavsdk_rpc_telemetry_GpsGlobalOrigin, GpsGlobalOrigin__Output as _mavsdk_rpc_telemetry_GpsGlobalOrigin__Output } from '../../../mavsdk/rpc/telemetry/GpsGlobalOrigin.js';

export interface GetGpsGlobalOriginResponse {
  'telemetry_result'?: (_mavsdk_rpc_telemetry_TelemetryResult | null);
  'gps_global_origin'?: (_mavsdk_rpc_telemetry_GpsGlobalOrigin | null);
}

export interface GetGpsGlobalOriginResponse__Output {
  'telemetry_result': (_mavsdk_rpc_telemetry_TelemetryResult__Output | null);
  'gps_global_origin': (_mavsdk_rpc_telemetry_GpsGlobalOrigin__Output | null);
}
