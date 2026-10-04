// Original file: proto/action/action.proto


export interface GotoLocationRequest {
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
  'yaw_deg'?: (number | string);
}

export interface GotoLocationRequest__Output {
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
  'yaw_deg': (number);
}
