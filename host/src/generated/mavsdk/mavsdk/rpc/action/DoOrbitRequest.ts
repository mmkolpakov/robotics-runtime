// Original file: proto/action/action.proto

import type { OrbitYawBehavior as _mavsdk_rpc_action_OrbitYawBehavior, OrbitYawBehavior__Output as _mavsdk_rpc_action_OrbitYawBehavior__Output } from '../../../mavsdk/rpc/action/OrbitYawBehavior.js';

export interface DoOrbitRequest {
  'radius_m'?: (number | string);
  'velocity_ms'?: (number | string);
  'yaw_behavior'?: (_mavsdk_rpc_action_OrbitYawBehavior);
  'latitude_deg'?: (number | string);
  'longitude_deg'?: (number | string);
  'absolute_altitude_m'?: (number | string);
}

export interface DoOrbitRequest__Output {
  'radius_m': (number);
  'velocity_ms': (number);
  'yaw_behavior': (_mavsdk_rpc_action_OrbitYawBehavior__Output);
  'latitude_deg': (number);
  'longitude_deg': (number);
  'absolute_altitude_m': (number);
}
