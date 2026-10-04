// Original file: proto/telemetry/telemetry.proto

import type { StatusTextType as _mavsdk_rpc_telemetry_StatusTextType, StatusTextType__Output as _mavsdk_rpc_telemetry_StatusTextType__Output } from '../../../mavsdk/rpc/telemetry/StatusTextType.js';

export interface StatusText {
  'type'?: (_mavsdk_rpc_telemetry_StatusTextType);
  'text'?: (string);
}

export interface StatusText__Output {
  'type': (_mavsdk_rpc_telemetry_StatusTextType__Output);
  'text': (string);
}
