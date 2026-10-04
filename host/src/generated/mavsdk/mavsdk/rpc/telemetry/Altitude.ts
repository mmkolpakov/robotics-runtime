// Original file: proto/telemetry/telemetry.proto

import type { Long } from '@grpc/proto-loader';

export interface Altitude {
  'altitude_monotonic_m'?: (number | string);
  'altitude_amsl_m'?: (number | string);
  'altitude_local_m'?: (number | string);
  'altitude_relative_m'?: (number | string);
  'altitude_terrain_m'?: (number | string);
  'bottom_clearance_m'?: (number | string);
  'timestamp_us'?: (number | string | Long);
}

export interface Altitude__Output {
  'altitude_monotonic_m': (number);
  'altitude_amsl_m': (number);
  'altitude_local_m': (number);
  'altitude_relative_m': (number);
  'altitude_terrain_m': (number);
  'bottom_clearance_m': (number);
  'timestamp_us': (string);
}
