// Original file: proto/telemetry/telemetry.proto


export interface Health {
  'is_gyrometer_calibration_ok'?: (boolean);
  'is_accelerometer_calibration_ok'?: (boolean);
  'is_magnetometer_calibration_ok'?: (boolean);
  'is_local_position_ok'?: (boolean);
  'is_global_position_ok'?: (boolean);
  'is_home_position_ok'?: (boolean);
  'is_armable'?: (boolean);
}

export interface Health__Output {
  'is_gyrometer_calibration_ok': (boolean);
  'is_accelerometer_calibration_ok': (boolean);
  'is_magnetometer_calibration_ok': (boolean);
  'is_local_position_ok': (boolean);
  'is_global_position_ok': (boolean);
  'is_home_position_ok': (boolean);
  'is_armable': (boolean);
}
