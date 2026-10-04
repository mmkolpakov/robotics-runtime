// Original file: proto/action/action.proto

import type { ActionResult as _mavsdk_rpc_action_ActionResult, ActionResult__Output as _mavsdk_rpc_action_ActionResult__Output } from '../../../mavsdk/rpc/action/ActionResult.js';

export interface GetReturnToLaunchAltitudeResponse {
  'action_result'?: (_mavsdk_rpc_action_ActionResult | null);
  'relative_altitude_m'?: (number | string);
}

export interface GetReturnToLaunchAltitudeResponse__Output {
  'action_result': (_mavsdk_rpc_action_ActionResult__Output | null);
  'relative_altitude_m': (number);
}
