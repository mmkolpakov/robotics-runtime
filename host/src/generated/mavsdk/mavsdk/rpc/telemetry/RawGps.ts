// Original file: proto/telemetry/telemetry.proto

import type { Long } from '@grpc/proto-loader';

export interface RawGps {
  'timestamp_us'?: (number | string | Long);
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
  'hdop'?: (number | string);
  'vdop'?: (number | string);
  'velocity_m_s'?: (number | string);
  'cog_deg'?: (number | string);
  'altitude_ellipsoid_m'?: (number | string);
  'horizontal_uncertainty_m'?: (number | string);
  'vertical_uncertainty_m'?: (number | string);
  'velocity_uncertainty_m_s'?: (number | string);
  'heading_uncertainty_deg'?: (number | string);
  'yaw_deg'?: (number | string);
}

export interface RawGps__Output {
  'timestamp_us': (string);
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
  'hdop': (number);
  'vdop': (number);
  'velocity_m_s': (number);
  'cog_deg': (number);
  'altitude_ellipsoid_m': (number);
  'horizontal_uncertainty_m': (number);
  'vertical_uncertainty_m': (number);
  'velocity_uncertainty_m_s': (number);
  'heading_uncertainty_deg': (number);
  'yaw_deg': (number);
}
