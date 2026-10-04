// Original file: null

import type { FeatureSet as _google_protobuf_FeatureSet, FeatureSet__Output as _google_protobuf_FeatureSet__Output } from '../../google/protobuf/FeatureSet.js';
import type { UninterpretedOption as _google_protobuf_UninterpretedOption, UninterpretedOption__Output as _google_protobuf_UninterpretedOption__Output } from '../../google/protobuf/UninterpretedOption.js';
import type { AsyncType as _mavsdk_options_AsyncType, AsyncType__Output as _mavsdk_options_AsyncType__Output } from '../../mavsdk/options/AsyncType.js';

// Original file: null

export const _google_protobuf_MethodOptions_IdempotencyLevel = {
  IDEMPOTENCY_UNKNOWN: 'IDEMPOTENCY_UNKNOWN',
  NO_SIDE_EFFECTS: 'NO_SIDE_EFFECTS',
  IDEMPOTENT: 'IDEMPOTENT',
} as const;

export type _google_protobuf_MethodOptions_IdempotencyLevel =
  | 'IDEMPOTENCY_UNKNOWN'
  | 0
  | 'NO_SIDE_EFFECTS'
  | 1
  | 'IDEMPOTENT'
  | 2

export type _google_protobuf_MethodOptions_IdempotencyLevel__Output = typeof _google_protobuf_MethodOptions_IdempotencyLevel[keyof typeof _google_protobuf_MethodOptions_IdempotencyLevel]

export interface MethodOptions {
  'deprecated'?: (boolean);
  'idempotencyLevel'?: (_google_protobuf_MethodOptions_IdempotencyLevel);
  'features'?: (_google_protobuf_FeatureSet | null);
  'uninterpretedOption'?: (_google_protobuf_UninterpretedOption)[];
  '.mavsdk.options.async_type'?: (_mavsdk_options_AsyncType);
  '.mavsdk.options.is_finite'?: (boolean);
}

export interface MethodOptions__Output {
  'deprecated': (boolean);
  'idempotencyLevel': (_google_protobuf_MethodOptions_IdempotencyLevel__Output);
  'features': (_google_protobuf_FeatureSet__Output | null);
  'uninterpretedOption': (_google_protobuf_UninterpretedOption__Output)[];
  '.mavsdk.options.async_type': (_mavsdk_options_AsyncType__Output);
  '.mavsdk.options.is_finite': (boolean);
}
