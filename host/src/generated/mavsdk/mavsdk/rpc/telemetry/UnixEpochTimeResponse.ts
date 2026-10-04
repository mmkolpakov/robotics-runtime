// Original file: proto/telemetry/telemetry.proto

import type { Long } from '@grpc/proto-loader';

export interface UnixEpochTimeResponse {
  'time_us'?: (number | string | Long);
}

export interface UnixEpochTimeResponse__Output {
  'time_us': (string);
}
