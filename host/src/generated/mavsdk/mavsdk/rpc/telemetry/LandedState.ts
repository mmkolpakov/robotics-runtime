// Original file: proto/telemetry/telemetry.proto

export const LandedState = {
  LANDED_STATE_UNKNOWN: 'LANDED_STATE_UNKNOWN',
  LANDED_STATE_ON_GROUND: 'LANDED_STATE_ON_GROUND',
  LANDED_STATE_IN_AIR: 'LANDED_STATE_IN_AIR',
  LANDED_STATE_TAKING_OFF: 'LANDED_STATE_TAKING_OFF',
  LANDED_STATE_LANDING: 'LANDED_STATE_LANDING',
} as const;

export type LandedState =
  | 'LANDED_STATE_UNKNOWN'
  | 0
  | 'LANDED_STATE_ON_GROUND'
  | 1
  | 'LANDED_STATE_IN_AIR'
  | 2
  | 'LANDED_STATE_TAKING_OFF'
  | 3
  | 'LANDED_STATE_LANDING'
  | 4

export type LandedState__Output = typeof LandedState[keyof typeof LandedState]
