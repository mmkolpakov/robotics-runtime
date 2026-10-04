// Original file: proto/action/action.proto


export interface SetActuatorRequest {
  'index'?: (number);
  'value'?: (number | string);
}

export interface SetActuatorRequest__Output {
  'index': (number);
  'value': (number);
}
