// Original file: proto/telemetry/telemetry.proto

import type { Quaternion as _mavsdk_rpc_telemetry_Quaternion, Quaternion__Output as _mavsdk_rpc_telemetry_Quaternion__Output } from '../../../mavsdk/rpc/telemetry/Quaternion.js';
import type { Long } from '@grpc/proto-loader';

export interface HomePosition {
  'timestamp_us'?: (number | string | Long);
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
  'relative_altitude_m'?: (number | string);
  'local_north_m'?: (number | string);
  'local_east_m'?: (number | string);
  'local_down_m'?: (number | string);
  'q'?: (_mavsdk_rpc_telemetry_Quaternion | null);
  'approach_north_m'?: (number | string);
  'approach_east_m'?: (number | string);
  'approach_down_m'?: (number | string);
}

export interface HomePosition__Output {
  'timestamp_us': (string);
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
  'relative_altitude_m': (number);
  'local_north_m': (number);
  'local_east_m': (number);
  'local_down_m': (number);
  'q': (_mavsdk_rpc_telemetry_Quaternion__Output | null);
  'approach_north_m': (number);
  'approach_east_m': (number);
  'approach_down_m': (number);
}
