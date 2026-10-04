// Original file: proto/telemetry/telemetry.proto

import type { AccelerationFrd as _mavsdk_rpc_telemetry_AccelerationFrd, AccelerationFrd__Output as _mavsdk_rpc_telemetry_AccelerationFrd__Output } from '../../../mavsdk/rpc/telemetry/AccelerationFrd.js';
import type { AngularVelocityFrd as _mavsdk_rpc_telemetry_AngularVelocityFrd, AngularVelocityFrd__Output as _mavsdk_rpc_telemetry_AngularVelocityFrd__Output } from '../../../mavsdk/rpc/telemetry/AngularVelocityFrd.js';
import type { MagneticFieldFrd as _mavsdk_rpc_telemetry_MagneticFieldFrd, MagneticFieldFrd__Output as _mavsdk_rpc_telemetry_MagneticFieldFrd__Output } from '../../../mavsdk/rpc/telemetry/MagneticFieldFrd.js';
import type { Long } from '@grpc/proto-loader';

export interface Imu {
  'acceleration_frd'?: (_mavsdk_rpc_telemetry_AccelerationFrd | null);
  'angular_velocity_frd'?: (_mavsdk_rpc_telemetry_AngularVelocityFrd | null);
  'magnetic_field_frd'?: (_mavsdk_rpc_telemetry_MagneticFieldFrd | null);
  'temperature_degc'?: (number | string);
  'timestamp_us'?: (number | string | Long);
}

export interface Imu__Output {
  'acceleration_frd': (_mavsdk_rpc_telemetry_AccelerationFrd__Output | null);
  'angular_velocity_frd': (_mavsdk_rpc_telemetry_AngularVelocityFrd__Output | null);
  'magnetic_field_frd': (_mavsdk_rpc_telemetry_MagneticFieldFrd__Output | null);
  'temperature_degc': (number);
  'timestamp_us': (string);
}
