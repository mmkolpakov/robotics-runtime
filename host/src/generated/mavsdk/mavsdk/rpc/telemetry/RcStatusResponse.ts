// Original file: proto/telemetry/telemetry.proto

import type { RcStatus as _mavsdk_rpc_telemetry_RcStatus, RcStatus__Output as _mavsdk_rpc_telemetry_RcStatus__Output } from '../../../mavsdk/rpc/telemetry/RcStatus.js';

export interface RcStatusResponse {
  'rc_status'?: (_mavsdk_rpc_telemetry_RcStatus | null);
}

export interface RcStatusResponse__Output {
  'rc_status': (_mavsdk_rpc_telemetry_RcStatus__Output | null);
}
