// Original file: proto/telemetry/telemetry.proto

import type { Long } from '@grpc/proto-loader';

export interface Quaternion {
  'w'?: (number | string);
  'x'?: (number | string);
  'y'?: (number | string);
  'z'?: (number | string);
  'timestamp_us'?: (number | string | Long);
}

export interface Quaternion__Output {
  'w': (number);
  'x': (number);
  'y': (number);
  'z': (number);
  'timestamp_us': (string);
}
