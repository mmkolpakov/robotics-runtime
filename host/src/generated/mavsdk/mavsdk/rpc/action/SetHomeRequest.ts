// Original file: proto/action/action.proto


export interface SetHomeRequest {
  'use_current_location'?: (boolean);
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
}

export interface SetHomeRequest__Output {
  'use_current_location': (boolean);
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
}
