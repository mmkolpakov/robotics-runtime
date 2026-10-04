// Original file: proto/telemetry/telemetry.proto


export interface FixedwingMetrics {
  'airspeed_m_s'?: (number | string);
  'throttle_percentage'?: (number | string);
  'climb_rate_m_s'?: (number | string);
  'groundspeed_m_s'?: (number | string);
  'heading_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
}

export interface FixedwingMetrics__Output {
  'airspeed_m_s': (number);
  'throttle_percentage': (number);
  'climb_rate_m_s': (number);
  'groundspeed_m_s': (number);
  'heading_deg': (number);
  'absolute_altitude_m': (number);
}
