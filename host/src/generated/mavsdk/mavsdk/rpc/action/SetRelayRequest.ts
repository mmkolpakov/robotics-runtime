// Original file: proto/action/action.proto

import type { RelayCommand as _mavsdk_rpc_action_RelayCommand, RelayCommand__Output as _mavsdk_rpc_action_RelayCommand__Output } from '../../../mavsdk/rpc/action/RelayCommand.js';

export interface SetRelayRequest {
  'index'?: (number);
  'setting'?: (_mavsdk_rpc_action_RelayCommand);
}

export interface SetRelayRequest__Output {
  'index': (number);
  'setting': (_mavsdk_rpc_action_RelayCommand__Output);
}
