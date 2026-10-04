// Original file: proto/mavsdk_options.proto

export const AsyncType = {
  ASYNC: 'ASYNC',
  SYNC: 'SYNC',
  BOTH: 'BOTH',
} as const;

export type AsyncType =
  | 'ASYNC'
  | 0
  | 'SYNC'
  | 1
  | 'BOTH'
  | 2

export type AsyncType__Output = typeof AsyncType[keyof typeof AsyncType]
