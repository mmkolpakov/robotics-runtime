// Original file: proto/telemetry/telemetry.proto


export interface RcStatus {
  'was_available_once'?: (boolean);
  'is_available'?: (boolean);
  'signal_strength_percent'?: (number | string);
}

export interface RcStatus__Output {
  'was_available_once': (boolean);
  'is_available': (boolean);
  'signal_strength_percent': (number);
}
