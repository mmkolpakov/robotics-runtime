// Original file: proto/telemetry/telemetry.proto

import type { Health as _mavsdk_rpc_telemetry_Health, Health__Output as _mavsdk_rpc_telemetry_Health__Output } from '../../../mavsdk/rpc/telemetry/Health.js';

export interface HealthResponse {
  'health'?: (_mavsdk_rpc_telemetry_Health | null);
}

export interface HealthResponse__Output {
  'health': (_mavsdk_rpc_telemetry_Health__Output | null);
}
