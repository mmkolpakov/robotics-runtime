// Original file: proto/telemetry/telemetry.proto

import type { FixType as _mavsdk_rpc_telemetry_FixType, FixType__Output as _mavsdk_rpc_telemetry_FixType__Output } from '../../../mavsdk/rpc/telemetry/FixType.js';

export interface GpsInfo {
  'num_satellites'?: (number);
  'fix_type'?: (_mavsdk_rpc_telemetry_FixType);
}

export interface GpsInfo__Output {
  'num_satellites': (number);
  'fix_type': (_mavsdk_rpc_telemetry_FixType__Output);
}
