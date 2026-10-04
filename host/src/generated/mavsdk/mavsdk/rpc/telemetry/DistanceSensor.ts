// Original file: proto/telemetry/telemetry.proto

import type { EulerAngle as _mavsdk_rpc_telemetry_EulerAngle, EulerAngle__Output as _mavsdk_rpc_telemetry_EulerAngle__Output } from '../../../mavsdk/rpc/telemetry/EulerAngle.js';

export interface DistanceSensor {
  'minimum_distance_m'?: (number | string);
  'maximum_distance_m'?: (number | string);
  'current_distance_m'?: (number | string);
  'orientation'?: (_mavsdk_rpc_telemetry_EulerAngle | null);
}

export interface DistanceSensor__Output {
  'minimum_distance_m': (number);
  'maximum_distance_m': (number);
  'current_distance_m': (number);
  'orientation': (_mavsdk_rpc_telemetry_EulerAngle__Output | null);
}
