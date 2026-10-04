// Original file: proto/telemetry/telemetry.proto

import type { Battery as _mavsdk_rpc_telemetry_Battery, Battery__Output as _mavsdk_rpc_telemetry_Battery__Output } from '../../../mavsdk/rpc/telemetry/Battery.js';

export interface BatteryResponse {
  'battery'?: (_mavsdk_rpc_telemetry_Battery | null);
}

export interface BatteryResponse__Output {
  'battery': (_mavsdk_rpc_telemetry_Battery__Output | null);
}
