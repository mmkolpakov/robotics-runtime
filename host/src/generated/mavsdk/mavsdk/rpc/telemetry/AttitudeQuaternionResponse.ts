// Original file: proto/telemetry/telemetry.proto

import type { Quaternion as _mavsdk_rpc_telemetry_Quaternion, Quaternion__Output as _mavsdk_rpc_telemetry_Quaternion__Output } from '../../../mavsdk/rpc/telemetry/Quaternion.js';

export interface AttitudeQuaternionResponse {
  'attitude_quaternion'?: (_mavsdk_rpc_telemetry_Quaternion | null);
}

export interface AttitudeQuaternionResponse__Output {
  'attitude_quaternion': (_mavsdk_rpc_telemetry_Quaternion__Output | null);
}
