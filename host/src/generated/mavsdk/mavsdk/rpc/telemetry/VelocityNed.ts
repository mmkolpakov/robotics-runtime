// Original file: proto/telemetry/telemetry.proto


export interface VelocityNed {
  'north_m_s'?: (number | string);
  'east_m_s'?: (number | string);
  'down_m_s'?: (number | string);
}

export interface VelocityNed__Output {
  'north_m_s': (number);
  'east_m_s': (number);
  'down_m_s': (number);
}
