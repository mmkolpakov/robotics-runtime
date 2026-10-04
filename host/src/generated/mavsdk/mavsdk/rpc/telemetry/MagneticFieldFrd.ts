// Original file: proto/telemetry/telemetry.proto


export interface MagneticFieldFrd {
  'forward_gauss'?: (number | string);
  'right_gauss'?: (number | string);
  'down_gauss'?: (number | string);
}

export interface MagneticFieldFrd__Output {
  'forward_gauss': (number);
  'right_gauss': (number);
  'down_gauss': (number);
}
