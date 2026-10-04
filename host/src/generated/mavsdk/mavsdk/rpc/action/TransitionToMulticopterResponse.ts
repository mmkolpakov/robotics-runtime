// Original file: proto/action/action.proto

import type { ActionResult as _mavsdk_rpc_action_ActionResult, ActionResult__Output as _mavsdk_rpc_action_ActionResult__Output } from '../../../mavsdk/rpc/action/ActionResult.js';

export interface TransitionToMulticopterResponse {
  'action_result'?: (_mavsdk_rpc_action_ActionResult | null);
}

export interface TransitionToMulticopterResponse__Output {
  'action_result': (_mavsdk_rpc_action_ActionResult__Output | null);
}
