// Original file: proto/action/action.proto

export const RelayCommand = {
  RELAY_COMMAND_ON: 'RELAY_COMMAND_ON',
  RELAY_COMMAND_OFF: 'RELAY_COMMAND_OFF',
} as const;

export type RelayCommand =
  | 'RELAY_COMMAND_ON'
  | 0
  | 'RELAY_COMMAND_OFF'
  | 1

export type RelayCommand__Output = typeof RelayCommand[keyof typeof RelayCommand]
