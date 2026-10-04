// Original file: proto/telemetry/telemetry.proto

export const VtolState = {
  VTOL_STATE_UNDEFINED: 'VTOL_STATE_UNDEFINED',
  VTOL_STATE_TRANSITION_TO_FW: 'VTOL_STATE_TRANSITION_TO_FW',
  VTOL_STATE_TRANSITION_TO_MC: 'VTOL_STATE_TRANSITION_TO_MC',
  VTOL_STATE_MC: 'VTOL_STATE_MC',
  VTOL_STATE_FW: 'VTOL_STATE_FW',
} as const;

export type VtolState =
  | 'VTOL_STATE_UNDEFINED'
  | 0
  | 'VTOL_STATE_TRANSITION_TO_FW'
  | 1
  | 'VTOL_STATE_TRANSITION_TO_MC'
  | 2
  | 'VTOL_STATE_MC'
  | 3
  | 'VTOL_STATE_FW'
  | 4

export type VtolState__Output = typeof VtolState[keyof typeof VtolState]
