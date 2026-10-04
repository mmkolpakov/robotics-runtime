// Original file: proto/action/action.proto


// Original file: proto/action/action.proto

export const _mavsdk_rpc_action_ActionResult_Result = {
  RESULT_UNKNOWN: 'RESULT_UNKNOWN',
  RESULT_SUCCESS: 'RESULT_SUCCESS',
  RESULT_NO_SYSTEM: 'RESULT_NO_SYSTEM',
  RESULT_CONNECTION_ERROR: 'RESULT_CONNECTION_ERROR',
  RESULT_BUSY: 'RESULT_BUSY',
  RESULT_COMMAND_DENIED: 'RESULT_COMMAND_DENIED',
  RESULT_COMMAND_DENIED_LANDED_STATE_UNKNOWN: 'RESULT_COMMAND_DENIED_LANDED_STATE_UNKNOWN',
  RESULT_COMMAND_DENIED_NOT_LANDED: 'RESULT_COMMAND_DENIED_NOT_LANDED',
  RESULT_TIMEOUT: 'RESULT_TIMEOUT',
  RESULT_VTOL_TRANSITION_SUPPORT_UNKNOWN: 'RESULT_VTOL_TRANSITION_SUPPORT_UNKNOWN',
  RESULT_NO_VTOL_TRANSITION_SUPPORT: 'RESULT_NO_VTOL_TRANSITION_SUPPORT',
  RESULT_PARAMETER_ERROR: 'RESULT_PARAMETER_ERROR',
  RESULT_UNSUPPORTED: 'RESULT_UNSUPPORTED',
  RESULT_FAILED: 'RESULT_FAILED',
  RESULT_INVALID_ARGUMENT: 'RESULT_INVALID_ARGUMENT',
} as const;

export type _mavsdk_rpc_action_ActionResult_Result =
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
  | 'RESULT_COMMAND_DENIED_LANDED_STATE_UNKNOWN'
  | 6
  | 'RESULT_COMMAND_DENIED_NOT_LANDED'
  | 7
  | 'RESULT_TIMEOUT'
  | 8
  | 'RESULT_VTOL_TRANSITION_SUPPORT_UNKNOWN'
  | 9
  | 'RESULT_NO_VTOL_TRANSITION_SUPPORT'
  | 10
  | 'RESULT_PARAMETER_ERROR'
  | 11
  | 'RESULT_UNSUPPORTED'
  | 12
  | 'RESULT_FAILED'
  | 13
  | 'RESULT_INVALID_ARGUMENT'
  | 14

export type _mavsdk_rpc_action_ActionResult_Result__Output = typeof _mavsdk_rpc_action_ActionResult_Result[keyof typeof _mavsdk_rpc_action_ActionResult_Result]

export interface ActionResult {
  'result'?: (_mavsdk_rpc_action_ActionResult_Result);
  'result_str'?: (string);
}

export interface ActionResult__Output {
  'result': (_mavsdk_rpc_action_ActionResult_Result__Output);
  'result_str': (string);
}
