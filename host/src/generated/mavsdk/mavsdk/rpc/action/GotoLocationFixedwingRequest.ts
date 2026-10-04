// Original file: proto/action/action.proto


export interface GotoLocationFixedwingRequest {
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
  'loiter_radius_m'?: (number | string);
}

export interface GotoLocationFixedwingRequest__Output {
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
  'loiter_radius_m': (number);
}
