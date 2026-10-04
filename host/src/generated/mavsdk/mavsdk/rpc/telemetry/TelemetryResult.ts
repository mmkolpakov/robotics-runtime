// Original file: proto/telemetry/telemetry.proto


// Original file: proto/telemetry/telemetry.proto

export const _mavsdk_rpc_telemetry_TelemetryResult_Result = {
  RESULT_UNKNOWN: 'RESULT_UNKNOWN',
  RESULT_SUCCESS: 'RESULT_SUCCESS',
  RESULT_NO_SYSTEM: 'RESULT_NO_SYSTEM',
  RESULT_CONNECTION_ERROR: 'RESULT_CONNECTION_ERROR',
  RESULT_BUSY: 'RESULT_BUSY',
  RESULT_COMMAND_DENIED: 'RESULT_COMMAND_DENIED',
  RESULT_TIMEOUT: 'RESULT_TIMEOUT',
  RESULT_UNSUPPORTED: 'RESULT_UNSUPPORTED',
} as const;

export type _mavsdk_rpc_telemetry_TelemetryResult_Result =
  | 'RESULT_UNKNOWN'
  | 0
  | 'RESULT_SUCCESS'
  | 1
  | 'RESULT_NO_SYSTEM'
  | 2
  | 'RESULT_CONNECTION_ERROR'
  | 3
  | 'RESULT_BUSY'
  | 4
  | 'RESULT_COMMAND_DENIED'
  | 5
  | 'RESULT_TIMEOUT'
  | 6
  | 'RESULT_UNSUPPORTED'
  | 7

export type _mavsdk_rpc_telemetry_TelemetryResult_Result__Output = typeof _mavsdk_rpc_telemetry_TelemetryResult_Result[keyof typeof _mavsdk_rpc_telemetry_TelemetryResult_Result]

export interface TelemetryResult {
  'result'?: (_mavsdk_rpc_telemetry_TelemetryResult_Result);
  'result_str'?: (string);
}

export interface TelemetryResult__Output {
  'result': (_mavsdk_rpc_telemetry_TelemetryResult_Result__Output);
  'result_str': (string);
}
