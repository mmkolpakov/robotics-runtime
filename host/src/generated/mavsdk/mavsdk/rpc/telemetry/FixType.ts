// Original file: proto/telemetry/telemetry.proto

export const FixType = {
  FIX_TYPE_NO_GPS: 'FIX_TYPE_NO_GPS',
  FIX_TYPE_NO_FIX: 'FIX_TYPE_NO_FIX',
  FIX_TYPE_FIX_2D: 'FIX_TYPE_FIX_2D',
  FIX_TYPE_FIX_3D: 'FIX_TYPE_FIX_3D',
  FIX_TYPE_FIX_DGPS: 'FIX_TYPE_FIX_DGPS',
  FIX_TYPE_RTK_FLOAT: 'FIX_TYPE_RTK_FLOAT',
  FIX_TYPE_RTK_FIXED: 'FIX_TYPE_RTK_FIXED',
} as const;

export type FixType =
  | 'FIX_TYPE_NO_GPS'
  | 0
  | 'FIX_TYPE_NO_FIX'
  | 1
  | 'FIX_TYPE_FIX_2D'
  | 2
  | 'FIX_TYPE_FIX_3D'
  | 3
  | 'FIX_TYPE_FIX_DGPS'
  | 4
  | 'FIX_TYPE_RTK_FLOAT'
  | 5
  | 'FIX_TYPE_RTK_FIXED'
  | 6

export type FixType__Output = typeof FixType[keyof typeof FixType]
