// Original file: proto/telemetry/telemetry.proto


export interface Wind {
  'wind_x_ned_m_s'?: (number | string);
  'wind_y_ned_m_s'?: (number | string);
  'wind_z_ned_m_s'?: (number | string);
  'horizontal_variability_stddev_m_s'?: (number | string);
  'vertical_variability_stddev_m_s'?: (number | string);
  'wind_altitude_msl_m'?: (number | string);
  'horizontal_wind_speed_accuracy_m_s'?: (number | string);
  'vertical_wind_speed_accuracy_m_s'?: (number | string);
}

export interface Wind__Output {
  'wind_x_ned_m_s': (number);
  'wind_y_ned_m_s': (number);
  'wind_z_ned_m_s': (number);
  'horizontal_variability_stddev_m_s': (number);
  'vertical_variability_stddev_m_s': (number);
  'wind_altitude_msl_m': (number);
  'horizontal_wind_speed_accuracy_m_s': (number);
  'vertical_wind_speed_accuracy_m_s': (number);
}
