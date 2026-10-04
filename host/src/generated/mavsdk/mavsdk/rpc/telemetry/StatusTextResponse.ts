// Original file: proto/telemetry/telemetry.proto

import type { StatusText as _mavsdk_rpc_telemetry_StatusText, StatusText__Output as _mavsdk_rpc_telemetry_StatusText__Output } from '../../../mavsdk/rpc/telemetry/StatusText.js';

export interface StatusTextResponse {
  'status_text'?: (_mavsdk_rpc_telemetry_StatusText | null);
}

export interface StatusTextResponse__Output {
  'status_text': (_mavsdk_rpc_telemetry_StatusText__Output | null);
}
