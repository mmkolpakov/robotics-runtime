// Original file: proto/telemetry/telemetry.proto

import type { Long } from '@grpc/proto-loader';

export interface EulerAngle {
  'roll_deg'?: (number | string);
  'pitch_deg'?: (number | string);
  'yaw_deg'?: (number | string);
  'timestamp_us'?: (number | string | Long);
}

export interface EulerAngle__Output {
  'roll_deg': (number);
  'pitch_deg': (number);
  'yaw_deg': (number);
  'timestamp_us': (string);
}
