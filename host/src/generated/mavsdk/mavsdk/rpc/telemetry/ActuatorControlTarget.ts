// Original file: proto/telemetry/telemetry.proto


export interface ActuatorControlTarget {
  'group'?: (number);
  'controls'?: (number | string)[];
}

export interface ActuatorControlTarget__Output {
  'group': (number);
  'controls': (number)[];
}
