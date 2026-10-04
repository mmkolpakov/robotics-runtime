// Original file: proto/telemetry/telemetry.proto


export interface GpsGlobalOrigin {
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'altitude_m'?: (number | string);
}

export interface GpsGlobalOrigin__Output {
  'latitude_deg': (number);
  'longitude_deg': (number);
  'altitude_m': (number);
}
