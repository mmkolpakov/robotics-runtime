// Original file: proto/telemetry/telemetry.proto


export interface AccelerationFrd {
  'forward_m_s2'?: (number | string);
  'right_m_s2'?: (number | string);
  'down_m_s2'?: (number | string);
}

export interface AccelerationFrd__Output {
  'forward_m_s2': (number);
  'right_m_s2': (number);
  'down_m_s2': (number);
}
