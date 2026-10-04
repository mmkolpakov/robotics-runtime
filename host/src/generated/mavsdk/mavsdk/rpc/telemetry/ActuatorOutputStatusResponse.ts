// Original file: proto/telemetry/telemetry.proto

import type { ActuatorOutputStatus as _mavsdk_rpc_telemetry_ActuatorOutputStatus, ActuatorOutputStatus__Output as _mavsdk_rpc_telemetry_ActuatorOutputStatus__Output } from '../../../mavsdk/rpc/telemetry/ActuatorOutputStatus.js';

export interface ActuatorOutputStatusResponse {
  'actuator_output_status'?: (_mavsdk_rpc_telemetry_ActuatorOutputStatus | null);
}

export interface ActuatorOutputStatusResponse__Output {
  'actuator_output_status': (_mavsdk_rpc_telemetry_ActuatorOutputStatus__Output | null);
}
