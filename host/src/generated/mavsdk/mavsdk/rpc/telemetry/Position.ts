// Original file: proto/telemetry/telemetry.proto


export interface Position {
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
  'relative_altitude_m'?: (number | string);
}

export interface Position__Output {
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
  'relative_altitude_m': (number);
}
