// Original file: proto/telemetry/telemetry.proto


export interface PositionNed {
  'north_m'?: (number | string);
  'east_m'?: (number | string);
  'down_m'?: (number | string);
}

export interface PositionNed__Output {
  'north_m': (number);
  'east_m': (number);
  'down_m': (number);
}
