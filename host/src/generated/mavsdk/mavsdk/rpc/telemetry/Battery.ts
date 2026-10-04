// Original file: proto/telemetry/telemetry.proto

import type { BatteryFunction as _mavsdk_rpc_telemetry_BatteryFunction, BatteryFunction__Output as _mavsdk_rpc_telemetry_BatteryFunction__Output } from '../../../mavsdk/rpc/telemetry/BatteryFunction.js';

export interface Battery {
  'id'?: (number);
  'temperature_degc'?: (number | string);
  'voltage_v'?: (number | string);
  'current_battery_a'?: (number | string);
  'capacity_consumed_ah'?: (number | string);
  'remaining_percent'?: (number | string);
  'time_remaining_s'?: (number | string);
  'battery_function'?: (_mavsdk_rpc_telemetry_BatteryFunction);
}

export interface Battery__Output {
  'id': (number);
  'temperature_degc': (number);
  'voltage_v': (number);
  'current_battery_a': (number);
  'capacity_consumed_ah': (number);
  'remaining_percent': (number);
  'time_remaining_s': (number);
  'battery_function': (_mavsdk_rpc_telemetry_BatteryFunction__Output);
}
