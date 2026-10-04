// Original file: proto/telemetry/telemetry.proto

import type { PositionBody as _mavsdk_rpc_telemetry_PositionBody, PositionBody__Output as _mavsdk_rpc_telemetry_PositionBody__Output } from '../../../mavsdk/rpc/telemetry/PositionBody.js';
import type { Quaternion as _mavsdk_rpc_telemetry_Quaternion, Quaternion__Output as _mavsdk_rpc_telemetry_Quaternion__Output } from '../../../mavsdk/rpc/telemetry/Quaternion.js';
import type { VelocityBody as _mavsdk_rpc_telemetry_VelocityBody, VelocityBody__Output as _mavsdk_rpc_telemetry_VelocityBody__Output } from '../../../mavsdk/rpc/telemetry/VelocityBody.js';
import type { AngularVelocityBody as _mavsdk_rpc_telemetry_AngularVelocityBody, AngularVelocityBody__Output as _mavsdk_rpc_telemetry_AngularVelocityBody__Output } from '../../../mavsdk/rpc/telemetry/AngularVelocityBody.js';
import type { Covariance as _mavsdk_rpc_telemetry_Covariance, Covariance__Output as _mavsdk_rpc_telemetry_Covariance__Output } from '../../../mavsdk/rpc/telemetry/Covariance.js';
import type { Long } from '@grpc/proto-loader';

// Original file: proto/telemetry/telemetry.proto

export const _mavsdk_rpc_telemetry_Odometry_MavFrame = {
  MAV_FRAME_UNDEF: 'MAV_FRAME_UNDEF',
  MAV_FRAME_BODY_NED: 'MAV_FRAME_BODY_NED',
  MAV_FRAME_VISION_NED: 'MAV_FRAME_VISION_NED',
  MAV_FRAME_ESTIM_NED: 'MAV_FRAME_ESTIM_NED',
} as const;

export type _mavsdk_rpc_telemetry_Odometry_MavFrame =
  | 'MAV_FRAME_UNDEF'
  | 0
  | 'MAV_FRAME_BODY_NED'
  | 8
  | 'MAV_FRAME_VISION_NED'
  | 16
  | 'MAV_FRAME_ESTIM_NED'
  | 18

export type _mavsdk_rpc_telemetry_Odometry_MavFrame__Output = typeof _mavsdk_rpc_telemetry_Odometry_MavFrame[keyof typeof _mavsdk_rpc_telemetry_Odometry_MavFrame]

export interface Odometry {
  'time_usec'?: (number | string | Long);
  'frame_id'?: (_mavsdk_rpc_telemetry_Odometry_MavFrame);
  'child_frame_id'?: (_mavsdk_rpc_telemetry_Odometry_MavFrame);
  'position_body'?: (_mavsdk_rpc_telemetry_PositionBody | null);
  'q'?: (_mavsdk_rpc_telemetry_Quaternion | null);
  'velocity_body'?: (_mavsdk_rpc_telemetry_VelocityBody | null);
  'angular_velocity_body'?: (_mavsdk_rpc_telemetry_AngularVelocityBody | null);
  'pose_covariance'?: (_mavsdk_rpc_telemetry_Covariance | null);
  'velocity_covariance'?: (_mavsdk_rpc_telemetry_Covariance | null);
}

export interface Odometry__Output {
  'time_usec': (string);
  'frame_id': (_mavsdk_rpc_telemetry_Odometry_MavFrame__Output);
  'child_frame_id': (_mavsdk_rpc_telemetry_Odometry_MavFrame__Output);
  'position_body': (_mavsdk_rpc_telemetry_PositionBody__Output | null);
  'q': (_mavsdk_rpc_telemetry_Quaternion__Output | null);
  'velocity_body': (_mavsdk_rpc_telemetry_VelocityBody__Output | null);
  'angular_velocity_body': (_mavsdk_rpc_telemetry_AngularVelocityBody__Output | null);
  'pose_covariance': (_mavsdk_rpc_telemetry_Covariance__Output | null);
  'velocity_covariance': (_mavsdk_rpc_telemetry_Covariance__Output | null);
}
