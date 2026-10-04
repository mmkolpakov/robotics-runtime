// Original file: proto/action/action.proto


export interface SetGpsGlobalOriginRequest {
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
}

export interface SetGpsGlobalOriginRequest__Output {
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
}
