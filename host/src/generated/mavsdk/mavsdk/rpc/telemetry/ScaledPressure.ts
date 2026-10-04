// Original file: proto/telemetry/telemetry.proto

import type { Long } from '@grpc/proto-loader';

export interface ScaledPressure {
  'timestamp_us'?: (number | string | Long);
  'absolute_pressure_hpa'?: (number | string);
  'differential_pressure_hpa'?: (number | string);
  'temperature_deg'?: (number | string);
  'differential_pressure_temperature_deg'?: (number | string);
}

export interface ScaledPressure__Output {
  'timestamp_us': (string);
  'absolute_pressure_hpa': (number);
  'differential_pressure_hpa': (number);
  'temperature_deg': (number);
  'differential_pressure_temperature_deg': (number);
}
