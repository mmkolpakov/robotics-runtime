// Original file: proto/telemetry/telemetry.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { ActuatorControlTargetResponse as _mavsdk_rpc_telemetry_ActuatorControlTargetResponse, ActuatorControlTargetResponse__Output as _mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output } from '../../../mavsdk/rpc/telemetry/ActuatorControlTargetResponse.js';
import type { ActuatorOutputStatusResponse as _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse, ActuatorOutputStatusResponse__Output as _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output } from '../../../mavsdk/rpc/telemetry/ActuatorOutputStatusResponse.js';
import type { AltitudeResponse as _mavsdk_rpc_telemetry_AltitudeResponse, AltitudeResponse__Output as _mavsdk_rpc_telemetry_AltitudeResponse__Output } from '../../../mavsdk/rpc/telemetry/AltitudeResponse.js';
import type { ArmedResponse as _mavsdk_rpc_telemetry_ArmedResponse, ArmedResponse__Output as _mavsdk_rpc_telemetry_ArmedResponse__Output } from '../../../mavsdk/rpc/telemetry/ArmedResponse.js';
import type { AttitudeAngularVelocityBodyResponse as _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse, AttitudeAngularVelocityBodyResponse__Output as _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output } from '../../../mavsdk/rpc/telemetry/AttitudeAngularVelocityBodyResponse.js';
import type { AttitudeEulerResponse as _mavsdk_rpc_telemetry_AttitudeEulerResponse, AttitudeEulerResponse__Output as _mavsdk_rpc_telemetry_AttitudeEulerResponse__Output } from '../../../mavsdk/rpc/telemetry/AttitudeEulerResponse.js';
import type { AttitudeQuaternionResponse as _mavsdk_rpc_telemetry_AttitudeQuaternionResponse, AttitudeQuaternionResponse__Output as _mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output } from '../../../mavsdk/rpc/telemetry/AttitudeQuaternionResponse.js';
import type { BatteryResponse as _mavsdk_rpc_telemetry_BatteryResponse, BatteryResponse__Output as _mavsdk_rpc_telemetry_BatteryResponse__Output } from '../../../mavsdk/rpc/telemetry/BatteryResponse.js';
import type { DistanceSensorResponse as _mavsdk_rpc_telemetry_DistanceSensorResponse, DistanceSensorResponse__Output as _mavsdk_rpc_telemetry_DistanceSensorResponse__Output } from '../../../mavsdk/rpc/telemetry/DistanceSensorResponse.js';
import type { FixedwingMetricsResponse as _mavsdk_rpc_telemetry_FixedwingMetricsResponse, FixedwingMetricsResponse__Output as _mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output } from '../../../mavsdk/rpc/telemetry/FixedwingMetricsResponse.js';
import type { FlightModeResponse as _mavsdk_rpc_telemetry_FlightModeResponse, FlightModeResponse__Output as _mavsdk_rpc_telemetry_FlightModeResponse__Output } from '../../../mavsdk/rpc/telemetry/FlightModeResponse.js';
import type { GetGpsGlobalOriginRequest as _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, GetGpsGlobalOriginRequest__Output as _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest__Output } from '../../../mavsdk/rpc/telemetry/GetGpsGlobalOriginRequest.js';
import type { GetGpsGlobalOriginResponse as _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse, GetGpsGlobalOriginResponse__Output as _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output } from '../../../mavsdk/rpc/telemetry/GetGpsGlobalOriginResponse.js';
import type { GpsInfoResponse as _mavsdk_rpc_telemetry_GpsInfoResponse, GpsInfoResponse__Output as _mavsdk_rpc_telemetry_GpsInfoResponse__Output } from '../../../mavsdk/rpc/telemetry/GpsInfoResponse.js';
import type { GroundTruthResponse as _mavsdk_rpc_telemetry_GroundTruthResponse, GroundTruthResponse__Output as _mavsdk_rpc_telemetry_GroundTruthResponse__Output } from '../../../mavsdk/rpc/telemetry/GroundTruthResponse.js';
import type { HeadingResponse as _mavsdk_rpc_telemetry_HeadingResponse, HeadingResponse__Output as _mavsdk_rpc_telemetry_HeadingResponse__Output } from '../../../mavsdk/rpc/telemetry/HeadingResponse.js';
import type { HealthAllOkResponse as _mavsdk_rpc_telemetry_HealthAllOkResponse, HealthAllOkResponse__Output as _mavsdk_rpc_telemetry_HealthAllOkResponse__Output } from '../../../mavsdk/rpc/telemetry/HealthAllOkResponse.js';
import type { HealthResponse as _mavsdk_rpc_telemetry_HealthResponse, HealthResponse__Output as _mavsdk_rpc_telemetry_HealthResponse__Output } from '../../../mavsdk/rpc/telemetry/HealthResponse.js';
import type { HomeResponse as _mavsdk_rpc_telemetry_HomeResponse, HomeResponse__Output as _mavsdk_rpc_telemetry_HomeResponse__Output } from '../../../mavsdk/rpc/telemetry/HomeResponse.js';
import type { ImuResponse as _mavsdk_rpc_telemetry_ImuResponse, ImuResponse__Output as _mavsdk_rpc_telemetry_ImuResponse__Output } from '../../../mavsdk/rpc/telemetry/ImuResponse.js';
import type { InAirResponse as _mavsdk_rpc_telemetry_InAirResponse, InAirResponse__Output as _mavsdk_rpc_telemetry_InAirResponse__Output } from '../../../mavsdk/rpc/telemetry/InAirResponse.js';
import type { LandedStateResponse as _mavsdk_rpc_telemetry_LandedStateResponse, LandedStateResponse__Output as _mavsdk_rpc_telemetry_LandedStateResponse__Output } from '../../../mavsdk/rpc/telemetry/LandedStateResponse.js';
import type { OdometryResponse as _mavsdk_rpc_telemetry_OdometryResponse, OdometryResponse__Output as _mavsdk_rpc_telemetry_OdometryResponse__Output } from '../../../mavsdk/rpc/telemetry/OdometryResponse.js';
import type { PositionResponse as _mavsdk_rpc_telemetry_PositionResponse, PositionResponse__Output as _mavsdk_rpc_telemetry_PositionResponse__Output } from '../../../mavsdk/rpc/telemetry/PositionResponse.js';
import type { PositionVelocityNedResponse as _mavsdk_rpc_telemetry_PositionVelocityNedResponse, PositionVelocityNedResponse__Output as _mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output } from '../../../mavsdk/rpc/telemetry/PositionVelocityNedResponse.js';
import type { RawGpsResponse as _mavsdk_rpc_telemetry_RawGpsResponse, RawGpsResponse__Output as _mavsdk_rpc_telemetry_RawGpsResponse__Output } from '../../../mavsdk/rpc/telemetry/RawGpsResponse.js';
import type { RawImuResponse as _mavsdk_rpc_telemetry_RawImuResponse, RawImuResponse__Output as _mavsdk_rpc_telemetry_RawImuResponse__Output } from '../../../mavsdk/rpc/telemetry/RawImuResponse.js';
import type { RcStatusResponse as _mavsdk_rpc_telemetry_RcStatusResponse, RcStatusResponse__Output as _mavsdk_rpc_telemetry_RcStatusResponse__Output } from '../../../mavsdk/rpc/telemetry/RcStatusResponse.js';
import type { ScaledImuResponse as _mavsdk_rpc_telemetry_ScaledImuResponse, ScaledImuResponse__Output as _mavsdk_rpc_telemetry_ScaledImuResponse__Output } from '../../../mavsdk/rpc/telemetry/ScaledImuResponse.js';
import type { ScaledPressureResponse as _mavsdk_rpc_telemetry_ScaledPressureResponse, ScaledPressureResponse__Output as _mavsdk_rpc_telemetry_ScaledPressureResponse__Output } from '../../../mavsdk/rpc/telemetry/ScaledPressureResponse.js';
import type { SetRateActuatorControlTargetRequest as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, SetRateActuatorControlTargetRequest__Output as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateActuatorControlTargetRequest.js';
import type { SetRateActuatorControlTargetResponse as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse, SetRateActuatorControlTargetResponse__Output as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateActuatorControlTargetResponse.js';
import type { SetRateActuatorOutputStatusRequest as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, SetRateActuatorOutputStatusRequest__Output as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateActuatorOutputStatusRequest.js';
import type { SetRateActuatorOutputStatusResponse as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse, SetRateActuatorOutputStatusResponse__Output as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateActuatorOutputStatusResponse.js';
import type { SetRateAltitudeRequest as _mavsdk_rpc_telemetry_SetRateAltitudeRequest, SetRateAltitudeRequest__Output as _mavsdk_rpc_telemetry_SetRateAltitudeRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateAltitudeRequest.js';
import type { SetRateAltitudeResponse as _mavsdk_rpc_telemetry_SetRateAltitudeResponse, SetRateAltitudeResponse__Output as _mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateAltitudeResponse.js';
import type { SetRateAttitudeEulerRequest as _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, SetRateAttitudeEulerRequest__Output as _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateAttitudeEulerRequest.js';
import type { SetRateAttitudeEulerResponse as _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse, SetRateAttitudeEulerResponse__Output as _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateAttitudeEulerResponse.js';
import type { SetRateAttitudeQuaternionRequest as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, SetRateAttitudeQuaternionRequest__Output as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateAttitudeQuaternionRequest.js';
import type { SetRateAttitudeQuaternionResponse as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse, SetRateAttitudeQuaternionResponse__Output as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateAttitudeQuaternionResponse.js';
import type { SetRateBatteryRequest as _mavsdk_rpc_telemetry_SetRateBatteryRequest, SetRateBatteryRequest__Output as _mavsdk_rpc_telemetry_SetRateBatteryRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateBatteryRequest.js';
import type { SetRateBatteryResponse as _mavsdk_rpc_telemetry_SetRateBatteryResponse, SetRateBatteryResponse__Output as _mavsdk_rpc_telemetry_SetRateBatteryResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateBatteryResponse.js';
import type { SetRateDistanceSensorRequest as _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, SetRateDistanceSensorRequest__Output as _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateDistanceSensorRequest.js';
import type { SetRateDistanceSensorResponse as _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse, SetRateDistanceSensorResponse__Output as _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateDistanceSensorResponse.js';
import type { SetRateFixedwingMetricsRequest as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, SetRateFixedwingMetricsRequest__Output as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateFixedwingMetricsRequest.js';
import type { SetRateFixedwingMetricsResponse as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse, SetRateFixedwingMetricsResponse__Output as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateFixedwingMetricsResponse.js';
import type { SetRateGpsInfoRequest as _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, SetRateGpsInfoRequest__Output as _mavsdk_rpc_telemetry_SetRateGpsInfoRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateGpsInfoRequest.js';
import type { SetRateGpsInfoResponse as _mavsdk_rpc_telemetry_SetRateGpsInfoResponse, SetRateGpsInfoResponse__Output as _mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateGpsInfoResponse.js';
import type { SetRateGroundTruthRequest as _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, SetRateGroundTruthRequest__Output as _mavsdk_rpc_telemetry_SetRateGroundTruthRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateGroundTruthRequest.js';
import type { SetRateGroundTruthResponse as _mavsdk_rpc_telemetry_SetRateGroundTruthResponse, SetRateGroundTruthResponse__Output as _mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateGroundTruthResponse.js';
import type { SetRateHealthRequest as _mavsdk_rpc_telemetry_SetRateHealthRequest, SetRateHealthRequest__Output as _mavsdk_rpc_telemetry_SetRateHealthRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateHealthRequest.js';
import type { SetRateHealthResponse as _mavsdk_rpc_telemetry_SetRateHealthResponse, SetRateHealthResponse__Output as _mavsdk_rpc_telemetry_SetRateHealthResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateHealthResponse.js';
import type { SetRateHomeRequest as _mavsdk_rpc_telemetry_SetRateHomeRequest, SetRateHomeRequest__Output as _mavsdk_rpc_telemetry_SetRateHomeRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateHomeRequest.js';
import type { SetRateHomeResponse as _mavsdk_rpc_telemetry_SetRateHomeResponse, SetRateHomeResponse__Output as _mavsdk_rpc_telemetry_SetRateHomeResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateHomeResponse.js';
import type { SetRateImuRequest as _mavsdk_rpc_telemetry_SetRateImuRequest, SetRateImuRequest__Output as _mavsdk_rpc_telemetry_SetRateImuRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateImuRequest.js';
import type { SetRateImuResponse as _mavsdk_rpc_telemetry_SetRateImuResponse, SetRateImuResponse__Output as _mavsdk_rpc_telemetry_SetRateImuResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateImuResponse.js';
import type { SetRateInAirRequest as _mavsdk_rpc_telemetry_SetRateInAirRequest, SetRateInAirRequest__Output as _mavsdk_rpc_telemetry_SetRateInAirRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateInAirRequest.js';
import type { SetRateInAirResponse as _mavsdk_rpc_telemetry_SetRateInAirResponse, SetRateInAirResponse__Output as _mavsdk_rpc_telemetry_SetRateInAirResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateInAirResponse.js';
import type { SetRateLandedStateRequest as _mavsdk_rpc_telemetry_SetRateLandedStateRequest, SetRateLandedStateRequest__Output as _mavsdk_rpc_telemetry_SetRateLandedStateRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateLandedStateRequest.js';
import type { SetRateLandedStateResponse as _mavsdk_rpc_telemetry_SetRateLandedStateResponse, SetRateLandedStateResponse__Output as _mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateLandedStateResponse.js';
import type { SetRateOdometryRequest as _mavsdk_rpc_telemetry_SetRateOdometryRequest, SetRateOdometryRequest__Output as _mavsdk_rpc_telemetry_SetRateOdometryRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateOdometryRequest.js';
import type { SetRateOdometryResponse as _mavsdk_rpc_telemetry_SetRateOdometryResponse, SetRateOdometryResponse__Output as _mavsdk_rpc_telemetry_SetRateOdometryResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateOdometryResponse.js';
import type { SetRatePositionRequest as _mavsdk_rpc_telemetry_SetRatePositionRequest, SetRatePositionRequest__Output as _mavsdk_rpc_telemetry_SetRatePositionRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRatePositionRequest.js';
import type { SetRatePositionResponse as _mavsdk_rpc_telemetry_SetRatePositionResponse, SetRatePositionResponse__Output as _mavsdk_rpc_telemetry_SetRatePositionResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRatePositionResponse.js';
import type { SetRatePositionVelocityNedRequest as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, SetRatePositionVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRatePositionVelocityNedRequest.js';
import type { SetRatePositionVelocityNedResponse as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse, SetRatePositionVelocityNedResponse__Output as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRatePositionVelocityNedResponse.js';
import type { SetRateRawGpsRequest as _mavsdk_rpc_telemetry_SetRateRawGpsRequest, SetRateRawGpsRequest__Output as _mavsdk_rpc_telemetry_SetRateRawGpsRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateRawGpsRequest.js';
import type { SetRateRawGpsResponse as _mavsdk_rpc_telemetry_SetRateRawGpsResponse, SetRateRawGpsResponse__Output as _mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateRawGpsResponse.js';
import type { SetRateRawImuRequest as _mavsdk_rpc_telemetry_SetRateRawImuRequest, SetRateRawImuRequest__Output as _mavsdk_rpc_telemetry_SetRateRawImuRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateRawImuRequest.js';
import type { SetRateRawImuResponse as _mavsdk_rpc_telemetry_SetRateRawImuResponse, SetRateRawImuResponse__Output as _mavsdk_rpc_telemetry_SetRateRawImuResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateRawImuResponse.js';
import type { SetRateRcStatusRequest as _mavsdk_rpc_telemetry_SetRateRcStatusRequest, SetRateRcStatusRequest__Output as _mavsdk_rpc_telemetry_SetRateRcStatusRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateRcStatusRequest.js';
import type { SetRateRcStatusResponse as _mavsdk_rpc_telemetry_SetRateRcStatusResponse, SetRateRcStatusResponse__Output as _mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateRcStatusResponse.js';
import type { SetRateScaledImuRequest as _mavsdk_rpc_telemetry_SetRateScaledImuRequest, SetRateScaledImuRequest__Output as _mavsdk_rpc_telemetry_SetRateScaledImuRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateScaledImuRequest.js';
import type { SetRateScaledImuResponse as _mavsdk_rpc_telemetry_SetRateScaledImuResponse, SetRateScaledImuResponse__Output as _mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateScaledImuResponse.js';
import type { SetRateUnixEpochTimeRequest as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, SetRateUnixEpochTimeRequest__Output as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateUnixEpochTimeRequest.js';
import type { SetRateUnixEpochTimeResponse as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse, SetRateUnixEpochTimeResponse__Output as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateUnixEpochTimeResponse.js';
import type { SetRateVelocityNedRequest as _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, SetRateVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SetRateVelocityNedRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateVelocityNedRequest.js';
import type { SetRateVelocityNedResponse as _mavsdk_rpc_telemetry_SetRateVelocityNedResponse, SetRateVelocityNedResponse__Output as _mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateVelocityNedResponse.js';
import type { SetRateVtolStateRequest as _mavsdk_rpc_telemetry_SetRateVtolStateRequest, SetRateVtolStateRequest__Output as _mavsdk_rpc_telemetry_SetRateVtolStateRequest__Output } from '../../../mavsdk/rpc/telemetry/SetRateVtolStateRequest.js';
import type { SetRateVtolStateResponse as _mavsdk_rpc_telemetry_SetRateVtolStateResponse, SetRateVtolStateResponse__Output as _mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output } from '../../../mavsdk/rpc/telemetry/SetRateVtolStateResponse.js';
import type { StatusTextResponse as _mavsdk_rpc_telemetry_StatusTextResponse, StatusTextResponse__Output as _mavsdk_rpc_telemetry_StatusTextResponse__Output } from '../../../mavsdk/rpc/telemetry/StatusTextResponse.js';
import type { SubscribeActuatorControlTargetRequest as _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, SubscribeActuatorControlTargetRequest__Output as _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeActuatorControlTargetRequest.js';
import type { SubscribeActuatorOutputStatusRequest as _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, SubscribeActuatorOutputStatusRequest__Output as _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeActuatorOutputStatusRequest.js';
import type { SubscribeAltitudeRequest as _mavsdk_rpc_telemetry_SubscribeAltitudeRequest, SubscribeAltitudeRequest__Output as _mavsdk_rpc_telemetry_SubscribeAltitudeRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeAltitudeRequest.js';
import type { SubscribeArmedRequest as _mavsdk_rpc_telemetry_SubscribeArmedRequest, SubscribeArmedRequest__Output as _mavsdk_rpc_telemetry_SubscribeArmedRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeArmedRequest.js';
import type { SubscribeAttitudeAngularVelocityBodyRequest as _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, SubscribeAttitudeAngularVelocityBodyRequest__Output as _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeAttitudeAngularVelocityBodyRequest.js';
import type { SubscribeAttitudeEulerRequest as _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, SubscribeAttitudeEulerRequest__Output as _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeAttitudeEulerRequest.js';
import type { SubscribeAttitudeQuaternionRequest as _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, SubscribeAttitudeQuaternionRequest__Output as _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeAttitudeQuaternionRequest.js';
import type { SubscribeBatteryRequest as _mavsdk_rpc_telemetry_SubscribeBatteryRequest, SubscribeBatteryRequest__Output as _mavsdk_rpc_telemetry_SubscribeBatteryRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeBatteryRequest.js';
import type { SubscribeDistanceSensorRequest as _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, SubscribeDistanceSensorRequest__Output as _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeDistanceSensorRequest.js';
import type { SubscribeFixedwingMetricsRequest as _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, SubscribeFixedwingMetricsRequest__Output as _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeFixedwingMetricsRequest.js';
import type { SubscribeFlightModeRequest as _mavsdk_rpc_telemetry_SubscribeFlightModeRequest, SubscribeFlightModeRequest__Output as _mavsdk_rpc_telemetry_SubscribeFlightModeRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeFlightModeRequest.js';
import type { SubscribeGpsInfoRequest as _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, SubscribeGpsInfoRequest__Output as _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeGpsInfoRequest.js';
import type { SubscribeGroundTruthRequest as _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, SubscribeGroundTruthRequest__Output as _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeGroundTruthRequest.js';
import type { SubscribeHeadingRequest as _mavsdk_rpc_telemetry_SubscribeHeadingRequest, SubscribeHeadingRequest__Output as _mavsdk_rpc_telemetry_SubscribeHeadingRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeHeadingRequest.js';
import type { SubscribeHealthAllOkRequest as _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, SubscribeHealthAllOkRequest__Output as _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeHealthAllOkRequest.js';
import type { SubscribeHealthRequest as _mavsdk_rpc_telemetry_SubscribeHealthRequest, SubscribeHealthRequest__Output as _mavsdk_rpc_telemetry_SubscribeHealthRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeHealthRequest.js';
import type { SubscribeHomeRequest as _mavsdk_rpc_telemetry_SubscribeHomeRequest, SubscribeHomeRequest__Output as _mavsdk_rpc_telemetry_SubscribeHomeRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeHomeRequest.js';
import type { SubscribeImuRequest as _mavsdk_rpc_telemetry_SubscribeImuRequest, SubscribeImuRequest__Output as _mavsdk_rpc_telemetry_SubscribeImuRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeImuRequest.js';
import type { SubscribeInAirRequest as _mavsdk_rpc_telemetry_SubscribeInAirRequest, SubscribeInAirRequest__Output as _mavsdk_rpc_telemetry_SubscribeInAirRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeInAirRequest.js';
import type { SubscribeLandedStateRequest as _mavsdk_rpc_telemetry_SubscribeLandedStateRequest, SubscribeLandedStateRequest__Output as _mavsdk_rpc_telemetry_SubscribeLandedStateRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeLandedStateRequest.js';
import type { SubscribeOdometryRequest as _mavsdk_rpc_telemetry_SubscribeOdometryRequest, SubscribeOdometryRequest__Output as _mavsdk_rpc_telemetry_SubscribeOdometryRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeOdometryRequest.js';
import type { SubscribePositionRequest as _mavsdk_rpc_telemetry_SubscribePositionRequest, SubscribePositionRequest__Output as _mavsdk_rpc_telemetry_SubscribePositionRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribePositionRequest.js';
import type { SubscribePositionVelocityNedRequest as _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, SubscribePositionVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribePositionVelocityNedRequest.js';
import type { SubscribeRawGpsRequest as _mavsdk_rpc_telemetry_SubscribeRawGpsRequest, SubscribeRawGpsRequest__Output as _mavsdk_rpc_telemetry_SubscribeRawGpsRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeRawGpsRequest.js';
import type { SubscribeRawImuRequest as _mavsdk_rpc_telemetry_SubscribeRawImuRequest, SubscribeRawImuRequest__Output as _mavsdk_rpc_telemetry_SubscribeRawImuRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeRawImuRequest.js';
import type { SubscribeRcStatusRequest as _mavsdk_rpc_telemetry_SubscribeRcStatusRequest, SubscribeRcStatusRequest__Output as _mavsdk_rpc_telemetry_SubscribeRcStatusRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeRcStatusRequest.js';
import type { SubscribeScaledImuRequest as _mavsdk_rpc_telemetry_SubscribeScaledImuRequest, SubscribeScaledImuRequest__Output as _mavsdk_rpc_telemetry_SubscribeScaledImuRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeScaledImuRequest.js';
import type { SubscribeScaledPressureRequest as _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, SubscribeScaledPressureRequest__Output as _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeScaledPressureRequest.js';
import type { SubscribeStatusTextRequest as _mavsdk_rpc_telemetry_SubscribeStatusTextRequest, SubscribeStatusTextRequest__Output as _mavsdk_rpc_telemetry_SubscribeStatusTextRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeStatusTextRequest.js';
import type { SubscribeUnixEpochTimeRequest as _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, SubscribeUnixEpochTimeRequest__Output as _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeUnixEpochTimeRequest.js';
import type { SubscribeVelocityNedRequest as _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, SubscribeVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeVelocityNedRequest.js';
import type { SubscribeVtolStateRequest as _mavsdk_rpc_telemetry_SubscribeVtolStateRequest, SubscribeVtolStateRequest__Output as _mavsdk_rpc_telemetry_SubscribeVtolStateRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeVtolStateRequest.js';
import type { SubscribeWindRequest as _mavsdk_rpc_telemetry_SubscribeWindRequest, SubscribeWindRequest__Output as _mavsdk_rpc_telemetry_SubscribeWindRequest__Output } from '../../../mavsdk/rpc/telemetry/SubscribeWindRequest.js';
import type { UnixEpochTimeResponse as _mavsdk_rpc_telemetry_UnixEpochTimeResponse, UnixEpochTimeResponse__Output as _mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output } from '../../../mavsdk/rpc/telemetry/UnixEpochTimeResponse.js';
import type { VelocityNedResponse as _mavsdk_rpc_telemetry_VelocityNedResponse, VelocityNedResponse__Output as _mavsdk_rpc_telemetry_VelocityNedResponse__Output } from '../../../mavsdk/rpc/telemetry/VelocityNedResponse.js';
import type { VtolStateResponse as _mavsdk_rpc_telemetry_VtolStateResponse, VtolStateResponse__Output as _mavsdk_rpc_telemetry_VtolStateResponse__Output } from '../../../mavsdk/rpc/telemetry/VtolStateResponse.js';
import type { WindResponse as _mavsdk_rpc_telemetry_WindResponse, WindResponse__Output as _mavsdk_rpc_telemetry_WindResponse__Output } from '../../../mavsdk/rpc/telemetry/WindResponse.js';

export interface TelemetryServiceClient extends grpc.Client {
  GetGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  GetGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  GetGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  GetGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  getGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  getGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  getGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  getGpsGlobalOrigin(argument: _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  SetRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  SetRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  SetRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  SetRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  SetRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  SetRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setRateAltitude(argument: _mavsdk_rpc_telemetry_SetRateAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  SetRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  SetRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  SetRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeEuler(argument: _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  SetRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  SetRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  SetRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  setRateAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  SetRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  SetRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  SetRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  setRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  setRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  setRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  setRateBattery(argument: _mavsdk_rpc_telemetry_SetRateBatteryRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  SetRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  SetRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  SetRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  setRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  setRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  setRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  setRateDistanceSensor(argument: _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  SetRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  SetRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  SetRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  setRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  setRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  setRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  setRateFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  SetRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  SetRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  SetRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  setRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  setRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  setRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  setRateGpsInfo(argument: _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  SetRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  SetRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  SetRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  setRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  setRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  setRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  setRateGroundTruth(argument: _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  SetRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  SetRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  SetRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  setRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  setRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  setRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  setRateHealth(argument: _mavsdk_rpc_telemetry_SetRateHealthRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHealthResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  SetRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  SetRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  SetRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  setRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  setRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  setRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  setRateHome(argument: _mavsdk_rpc_telemetry_SetRateHomeRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateHomeResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  setRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  setRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  setRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  setRateImu(argument: _mavsdk_rpc_telemetry_SetRateImuRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateImuResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  SetRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  SetRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  SetRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  setRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  setRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  setRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  setRateInAir(argument: _mavsdk_rpc_telemetry_SetRateInAirRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateInAirResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  SetRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  SetRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  SetRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  setRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  setRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  setRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  setRateLandedState(argument: _mavsdk_rpc_telemetry_SetRateLandedStateRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  SetRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  SetRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  SetRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  setRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  setRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  setRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  setRateOdometry(argument: _mavsdk_rpc_telemetry_SetRateOdometryRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>): grpc.ClientUnaryCall;
  
  SetRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  SetRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  SetRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  SetRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  setRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  setRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  setRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  setRatePosition(argument: _mavsdk_rpc_telemetry_SetRatePositionRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionResponse__Output>): grpc.ClientUnaryCall;
  
  SetRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  SetRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  SetRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  SetRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRatePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  SetRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  SetRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  SetRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  setRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  setRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  setRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  setRateRawGps(argument: _mavsdk_rpc_telemetry_SetRateRawGpsRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  setRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  setRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  setRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  setRateRawImu(argument: _mavsdk_rpc_telemetry_SetRateRawImuRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  SetRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  SetRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  SetRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  setRateRcStatus(argument: _mavsdk_rpc_telemetry_SetRateRcStatusRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  SetRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  setRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  setRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  setRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  setRateScaledImu(argument: _mavsdk_rpc_telemetry_SetRateScaledImuRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  SetRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  SetRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  SetRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  setRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  setRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  setRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  setRateUnixEpochTime(argument: _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  SetRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  SetRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  SetRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  setRateVelocityNed(argument: _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>): grpc.ClientUnaryCall;
  
  SetRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  SetRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  SetRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  SetRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  setRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  setRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  setRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  setRateVtolState(argument: _mavsdk_rpc_telemetry_SetRateVtolStateRequest, callback: grpc.requestCallback<_mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>): grpc.ClientUnaryCall;
  
  SubscribeActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output>;
  SubscribeActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output>;
  subscribeActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output>;
  subscribeActuatorControlTarget(argument: _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output>;
  
  SubscribeActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output>;
  SubscribeActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output>;
  subscribeActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output>;
  subscribeActuatorOutputStatus(argument: _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output>;
  
  SubscribeAltitude(argument: _mavsdk_rpc_telemetry_SubscribeAltitudeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AltitudeResponse__Output>;
  SubscribeAltitude(argument: _mavsdk_rpc_telemetry_SubscribeAltitudeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AltitudeResponse__Output>;
  subscribeAltitude(argument: _mavsdk_rpc_telemetry_SubscribeAltitudeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AltitudeResponse__Output>;
  subscribeAltitude(argument: _mavsdk_rpc_telemetry_SubscribeAltitudeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AltitudeResponse__Output>;
  
  SubscribeArmed(argument: _mavsdk_rpc_telemetry_SubscribeArmedRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ArmedResponse__Output>;
  SubscribeArmed(argument: _mavsdk_rpc_telemetry_SubscribeArmedRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ArmedResponse__Output>;
  subscribeArmed(argument: _mavsdk_rpc_telemetry_SubscribeArmedRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ArmedResponse__Output>;
  subscribeArmed(argument: _mavsdk_rpc_telemetry_SubscribeArmedRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ArmedResponse__Output>;
  
  SubscribeAttitudeAngularVelocityBody(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output>;
  SubscribeAttitudeAngularVelocityBody(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output>;
  subscribeAttitudeAngularVelocityBody(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output>;
  subscribeAttitudeAngularVelocityBody(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output>;
  
  SubscribeAttitudeEuler(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeEulerResponse__Output>;
  SubscribeAttitudeEuler(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeEulerResponse__Output>;
  subscribeAttitudeEuler(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeEulerResponse__Output>;
  subscribeAttitudeEuler(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeEulerResponse__Output>;
  
  SubscribeAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output>;
  SubscribeAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output>;
  subscribeAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output>;
  subscribeAttitudeQuaternion(argument: _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output>;
  
  SubscribeBattery(argument: _mavsdk_rpc_telemetry_SubscribeBatteryRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_BatteryResponse__Output>;
  SubscribeBattery(argument: _mavsdk_rpc_telemetry_SubscribeBatteryRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_BatteryResponse__Output>;
  subscribeBattery(argument: _mavsdk_rpc_telemetry_SubscribeBatteryRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_BatteryResponse__Output>;
  subscribeBattery(argument: _mavsdk_rpc_telemetry_SubscribeBatteryRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_BatteryResponse__Output>;
  
  SubscribeDistanceSensor(argument: _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_DistanceSensorResponse__Output>;
  SubscribeDistanceSensor(argument: _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_DistanceSensorResponse__Output>;
  subscribeDistanceSensor(argument: _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_DistanceSensorResponse__Output>;
  subscribeDistanceSensor(argument: _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_DistanceSensorResponse__Output>;
  
  SubscribeFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output>;
  SubscribeFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output>;
  subscribeFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output>;
  subscribeFixedwingMetrics(argument: _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output>;
  
  SubscribeFlightMode(argument: _mavsdk_rpc_telemetry_SubscribeFlightModeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FlightModeResponse__Output>;
  SubscribeFlightMode(argument: _mavsdk_rpc_telemetry_SubscribeFlightModeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FlightModeResponse__Output>;
  subscribeFlightMode(argument: _mavsdk_rpc_telemetry_SubscribeFlightModeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FlightModeResponse__Output>;
  subscribeFlightMode(argument: _mavsdk_rpc_telemetry_SubscribeFlightModeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_FlightModeResponse__Output>;
  
  SubscribeGpsInfo(argument: _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GpsInfoResponse__Output>;
  SubscribeGpsInfo(argument: _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GpsInfoResponse__Output>;
  subscribeGpsInfo(argument: _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GpsInfoResponse__Output>;
  subscribeGpsInfo(argument: _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GpsInfoResponse__Output>;
  
  SubscribeGroundTruth(argument: _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GroundTruthResponse__Output>;
  SubscribeGroundTruth(argument: _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GroundTruthResponse__Output>;
  subscribeGroundTruth(argument: _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GroundTruthResponse__Output>;
  subscribeGroundTruth(argument: _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_GroundTruthResponse__Output>;
  
  SubscribeHeading(argument: _mavsdk_rpc_telemetry_SubscribeHeadingRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HeadingResponse__Output>;
  SubscribeHeading(argument: _mavsdk_rpc_telemetry_SubscribeHeadingRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HeadingResponse__Output>;
  subscribeHeading(argument: _mavsdk_rpc_telemetry_SubscribeHeadingRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HeadingResponse__Output>;
  subscribeHeading(argument: _mavsdk_rpc_telemetry_SubscribeHeadingRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HeadingResponse__Output>;
  
  SubscribeHealth(argument: _mavsdk_rpc_telemetry_SubscribeHealthRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthResponse__Output>;
  SubscribeHealth(argument: _mavsdk_rpc_telemetry_SubscribeHealthRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthResponse__Output>;
  subscribeHealth(argument: _mavsdk_rpc_telemetry_SubscribeHealthRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthResponse__Output>;
  subscribeHealth(argument: _mavsdk_rpc_telemetry_SubscribeHealthRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthResponse__Output>;
  
  SubscribeHealthAllOk(argument: _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthAllOkResponse__Output>;
  SubscribeHealthAllOk(argument: _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthAllOkResponse__Output>;
  subscribeHealthAllOk(argument: _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthAllOkResponse__Output>;
  subscribeHealthAllOk(argument: _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HealthAllOkResponse__Output>;
  
  SubscribeHome(argument: _mavsdk_rpc_telemetry_SubscribeHomeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HomeResponse__Output>;
  SubscribeHome(argument: _mavsdk_rpc_telemetry_SubscribeHomeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HomeResponse__Output>;
  subscribeHome(argument: _mavsdk_rpc_telemetry_SubscribeHomeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HomeResponse__Output>;
  subscribeHome(argument: _mavsdk_rpc_telemetry_SubscribeHomeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_HomeResponse__Output>;
  
  SubscribeImu(argument: _mavsdk_rpc_telemetry_SubscribeImuRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ImuResponse__Output>;
  SubscribeImu(argument: _mavsdk_rpc_telemetry_SubscribeImuRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ImuResponse__Output>;
  subscribeImu(argument: _mavsdk_rpc_telemetry_SubscribeImuRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ImuResponse__Output>;
  subscribeImu(argument: _mavsdk_rpc_telemetry_SubscribeImuRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ImuResponse__Output>;
  
  SubscribeInAir(argument: _mavsdk_rpc_telemetry_SubscribeInAirRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_InAirResponse__Output>;
  SubscribeInAir(argument: _mavsdk_rpc_telemetry_SubscribeInAirRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_InAirResponse__Output>;
  subscribeInAir(argument: _mavsdk_rpc_telemetry_SubscribeInAirRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_InAirResponse__Output>;
  subscribeInAir(argument: _mavsdk_rpc_telemetry_SubscribeInAirRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_InAirResponse__Output>;
  
  SubscribeLandedState(argument: _mavsdk_rpc_telemetry_SubscribeLandedStateRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_LandedStateResponse__Output>;
  SubscribeLandedState(argument: _mavsdk_rpc_telemetry_SubscribeLandedStateRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_LandedStateResponse__Output>;
  subscribeLandedState(argument: _mavsdk_rpc_telemetry_SubscribeLandedStateRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_LandedStateResponse__Output>;
  subscribeLandedState(argument: _mavsdk_rpc_telemetry_SubscribeLandedStateRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_LandedStateResponse__Output>;
  
  SubscribeOdometry(argument: _mavsdk_rpc_telemetry_SubscribeOdometryRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_OdometryResponse__Output>;
  SubscribeOdometry(argument: _mavsdk_rpc_telemetry_SubscribeOdometryRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_OdometryResponse__Output>;
  subscribeOdometry(argument: _mavsdk_rpc_telemetry_SubscribeOdometryRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_OdometryResponse__Output>;
  subscribeOdometry(argument: _mavsdk_rpc_telemetry_SubscribeOdometryRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_OdometryResponse__Output>;
  
  SubscribePosition(argument: _mavsdk_rpc_telemetry_SubscribePositionRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionResponse__Output>;
  SubscribePosition(argument: _mavsdk_rpc_telemetry_SubscribePositionRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionResponse__Output>;
  subscribePosition(argument: _mavsdk_rpc_telemetry_SubscribePositionRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionResponse__Output>;
  subscribePosition(argument: _mavsdk_rpc_telemetry_SubscribePositionRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionResponse__Output>;
  
  SubscribePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output>;
  SubscribePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output>;
  subscribePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output>;
  subscribePositionVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output>;
  
  SubscribeRawGps(argument: _mavsdk_rpc_telemetry_SubscribeRawGpsRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawGpsResponse__Output>;
  SubscribeRawGps(argument: _mavsdk_rpc_telemetry_SubscribeRawGpsRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawGpsResponse__Output>;
  subscribeRawGps(argument: _mavsdk_rpc_telemetry_SubscribeRawGpsRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawGpsResponse__Output>;
  subscribeRawGps(argument: _mavsdk_rpc_telemetry_SubscribeRawGpsRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawGpsResponse__Output>;
  
  SubscribeRawImu(argument: _mavsdk_rpc_telemetry_SubscribeRawImuRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawImuResponse__Output>;
  SubscribeRawImu(argument: _mavsdk_rpc_telemetry_SubscribeRawImuRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawImuResponse__Output>;
  subscribeRawImu(argument: _mavsdk_rpc_telemetry_SubscribeRawImuRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawImuResponse__Output>;
  subscribeRawImu(argument: _mavsdk_rpc_telemetry_SubscribeRawImuRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RawImuResponse__Output>;
  
  SubscribeRcStatus(argument: _mavsdk_rpc_telemetry_SubscribeRcStatusRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RcStatusResponse__Output>;
  SubscribeRcStatus(argument: _mavsdk_rpc_telemetry_SubscribeRcStatusRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RcStatusResponse__Output>;
  subscribeRcStatus(argument: _mavsdk_rpc_telemetry_SubscribeRcStatusRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RcStatusResponse__Output>;
  subscribeRcStatus(argument: _mavsdk_rpc_telemetry_SubscribeRcStatusRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_RcStatusResponse__Output>;
  
  SubscribeScaledImu(argument: _mavsdk_rpc_telemetry_SubscribeScaledImuRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledImuResponse__Output>;
  SubscribeScaledImu(argument: _mavsdk_rpc_telemetry_SubscribeScaledImuRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledImuResponse__Output>;
  subscribeScaledImu(argument: _mavsdk_rpc_telemetry_SubscribeScaledImuRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledImuResponse__Output>;
  subscribeScaledImu(argument: _mavsdk_rpc_telemetry_SubscribeScaledImuRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledImuResponse__Output>;
  
  SubscribeScaledPressure(argument: _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledPressureResponse__Output>;
  SubscribeScaledPressure(argument: _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledPressureResponse__Output>;
  subscribeScaledPressure(argument: _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledPressureResponse__Output>;
  subscribeScaledPressure(argument: _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_ScaledPressureResponse__Output>;
  
  SubscribeStatusText(argument: _mavsdk_rpc_telemetry_SubscribeStatusTextRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_StatusTextResponse__Output>;
  SubscribeStatusText(argument: _mavsdk_rpc_telemetry_SubscribeStatusTextRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_StatusTextResponse__Output>;
  subscribeStatusText(argument: _mavsdk_rpc_telemetry_SubscribeStatusTextRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_StatusTextResponse__Output>;
  subscribeStatusText(argument: _mavsdk_rpc_telemetry_SubscribeStatusTextRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_StatusTextResponse__Output>;
  
  SubscribeUnixEpochTime(argument: _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output>;
  SubscribeUnixEpochTime(argument: _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output>;
  subscribeUnixEpochTime(argument: _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output>;
  subscribeUnixEpochTime(argument: _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output>;
  
  SubscribeVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VelocityNedResponse__Output>;
  SubscribeVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VelocityNedResponse__Output>;
  subscribeVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VelocityNedResponse__Output>;
  subscribeVelocityNed(argument: _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VelocityNedResponse__Output>;
  
  SubscribeVtolState(argument: _mavsdk_rpc_telemetry_SubscribeVtolStateRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VtolStateResponse__Output>;
  SubscribeVtolState(argument: _mavsdk_rpc_telemetry_SubscribeVtolStateRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VtolStateResponse__Output>;
  subscribeVtolState(argument: _mavsdk_rpc_telemetry_SubscribeVtolStateRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VtolStateResponse__Output>;
  subscribeVtolState(argument: _mavsdk_rpc_telemetry_SubscribeVtolStateRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_VtolStateResponse__Output>;
  
  SubscribeWind(argument: _mavsdk_rpc_telemetry_SubscribeWindRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_WindResponse__Output>;
  SubscribeWind(argument: _mavsdk_rpc_telemetry_SubscribeWindRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_WindResponse__Output>;
  subscribeWind(argument: _mavsdk_rpc_telemetry_SubscribeWindRequest, metadata: grpc.Metadata, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_WindResponse__Output>;
  subscribeWind(argument: _mavsdk_rpc_telemetry_SubscribeWindRequest, options?: grpc.CallOptions): grpc.ClientReadableStream<_mavsdk_rpc_telemetry_WindResponse__Output>;
  
}

export interface TelemetryServiceHandlers extends grpc.UntypedServiceImplementation {
  GetGpsGlobalOrigin: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest__Output, _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse>;
  
  SetRateActuatorControlTarget: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest__Output, _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse>;
  
  SetRateActuatorOutputStatus: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest__Output, _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse>;
  
  SetRateAltitude: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateAltitudeRequest__Output, _mavsdk_rpc_telemetry_SetRateAltitudeResponse>;
  
  SetRateAttitudeEuler: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest__Output, _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse>;
  
  SetRateAttitudeQuaternion: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest__Output, _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse>;
  
  SetRateBattery: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateBatteryRequest__Output, _mavsdk_rpc_telemetry_SetRateBatteryResponse>;
  
  SetRateDistanceSensor: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateDistanceSensorRequest__Output, _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse>;
  
  SetRateFixedwingMetrics: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest__Output, _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse>;
  
  SetRateGpsInfo: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateGpsInfoRequest__Output, _mavsdk_rpc_telemetry_SetRateGpsInfoResponse>;
  
  SetRateGroundTruth: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateGroundTruthRequest__Output, _mavsdk_rpc_telemetry_SetRateGroundTruthResponse>;
  
  SetRateHealth: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateHealthRequest__Output, _mavsdk_rpc_telemetry_SetRateHealthResponse>;
  
  SetRateHome: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateHomeRequest__Output, _mavsdk_rpc_telemetry_SetRateHomeResponse>;
  
  SetRateImu: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateImuRequest__Output, _mavsdk_rpc_telemetry_SetRateImuResponse>;
  
  SetRateInAir: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateInAirRequest__Output, _mavsdk_rpc_telemetry_SetRateInAirResponse>;
  
  SetRateLandedState: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateLandedStateRequest__Output, _mavsdk_rpc_telemetry_SetRateLandedStateResponse>;
  
  SetRateOdometry: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateOdometryRequest__Output, _mavsdk_rpc_telemetry_SetRateOdometryResponse>;
  
  SetRatePosition: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRatePositionRequest__Output, _mavsdk_rpc_telemetry_SetRatePositionResponse>;
  
  SetRatePositionVelocityNed: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest__Output, _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse>;
  
  SetRateRawGps: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateRawGpsRequest__Output, _mavsdk_rpc_telemetry_SetRateRawGpsResponse>;
  
  SetRateRawImu: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateRawImuRequest__Output, _mavsdk_rpc_telemetry_SetRateRawImuResponse>;
  
  SetRateRcStatus: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateRcStatusRequest__Output, _mavsdk_rpc_telemetry_SetRateRcStatusResponse>;
  
  SetRateScaledImu: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateScaledImuRequest__Output, _mavsdk_rpc_telemetry_SetRateScaledImuResponse>;
  
  SetRateUnixEpochTime: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest__Output, _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse>;
  
  SetRateVelocityNed: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateVelocityNedRequest__Output, _mavsdk_rpc_telemetry_SetRateVelocityNedResponse>;
  
  SetRateVtolState: grpc.handleUnaryCall<_mavsdk_rpc_telemetry_SetRateVtolStateRequest__Output, _mavsdk_rpc_telemetry_SetRateVtolStateResponse>;
  
  SubscribeActuatorControlTarget: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest__Output, _mavsdk_rpc_telemetry_ActuatorControlTargetResponse>;
  
  SubscribeActuatorOutputStatus: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest__Output, _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse>;
  
  SubscribeAltitude: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeAltitudeRequest__Output, _mavsdk_rpc_telemetry_AltitudeResponse>;
  
  SubscribeArmed: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeArmedRequest__Output, _mavsdk_rpc_telemetry_ArmedResponse>;
  
  SubscribeAttitudeAngularVelocityBody: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest__Output, _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse>;
  
  SubscribeAttitudeEuler: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest__Output, _mavsdk_rpc_telemetry_AttitudeEulerResponse>;
  
  SubscribeAttitudeQuaternion: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest__Output, _mavsdk_rpc_telemetry_AttitudeQuaternionResponse>;
  
  SubscribeBattery: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeBatteryRequest__Output, _mavsdk_rpc_telemetry_BatteryResponse>;
  
  SubscribeDistanceSensor: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest__Output, _mavsdk_rpc_telemetry_DistanceSensorResponse>;
  
  SubscribeFixedwingMetrics: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest__Output, _mavsdk_rpc_telemetry_FixedwingMetricsResponse>;
  
  SubscribeFlightMode: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeFlightModeRequest__Output, _mavsdk_rpc_telemetry_FlightModeResponse>;
  
  SubscribeGpsInfo: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeGpsInfoRequest__Output, _mavsdk_rpc_telemetry_GpsInfoResponse>;
  
  SubscribeGroundTruth: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeGroundTruthRequest__Output, _mavsdk_rpc_telemetry_GroundTruthResponse>;
  
  SubscribeHeading: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeHeadingRequest__Output, _mavsdk_rpc_telemetry_HeadingResponse>;
  
  SubscribeHealth: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeHealthRequest__Output, _mavsdk_rpc_telemetry_HealthResponse>;
  
  SubscribeHealthAllOk: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest__Output, _mavsdk_rpc_telemetry_HealthAllOkResponse>;
  
  SubscribeHome: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeHomeRequest__Output, _mavsdk_rpc_telemetry_HomeResponse>;
  
  SubscribeImu: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeImuRequest__Output, _mavsdk_rpc_telemetry_ImuResponse>;
  
  SubscribeInAir: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeInAirRequest__Output, _mavsdk_rpc_telemetry_InAirResponse>;
  
  SubscribeLandedState: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeLandedStateRequest__Output, _mavsdk_rpc_telemetry_LandedStateResponse>;
  
  SubscribeOdometry: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeOdometryRequest__Output, _mavsdk_rpc_telemetry_OdometryResponse>;
  
  SubscribePosition: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribePositionRequest__Output, _mavsdk_rpc_telemetry_PositionResponse>;
  
  SubscribePositionVelocityNed: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest__Output, _mavsdk_rpc_telemetry_PositionVelocityNedResponse>;
  
  SubscribeRawGps: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeRawGpsRequest__Output, _mavsdk_rpc_telemetry_RawGpsResponse>;
  
  SubscribeRawImu: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeRawImuRequest__Output, _mavsdk_rpc_telemetry_RawImuResponse>;
  
  SubscribeRcStatus: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeRcStatusRequest__Output, _mavsdk_rpc_telemetry_RcStatusResponse>;
  
  SubscribeScaledImu: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeScaledImuRequest__Output, _mavsdk_rpc_telemetry_ScaledImuResponse>;
  
  SubscribeScaledPressure: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeScaledPressureRequest__Output, _mavsdk_rpc_telemetry_ScaledPressureResponse>;
  
  SubscribeStatusText: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeStatusTextRequest__Output, _mavsdk_rpc_telemetry_StatusTextResponse>;
  
  SubscribeUnixEpochTime: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest__Output, _mavsdk_rpc_telemetry_UnixEpochTimeResponse>;
  
  SubscribeVelocityNed: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeVelocityNedRequest__Output, _mavsdk_rpc_telemetry_VelocityNedResponse>;
  
  SubscribeVtolState: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeVtolStateRequest__Output, _mavsdk_rpc_telemetry_VtolStateResponse>;
  
  SubscribeWind: grpc.handleServerStreamingCall<_mavsdk_rpc_telemetry_SubscribeWindRequest__Output, _mavsdk_rpc_telemetry_WindResponse>;
  
}

export interface TelemetryServiceDefinition extends grpc.ServiceDefinition {
  GetGpsGlobalOrigin: MethodDefinition<_mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse, _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest__Output, _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>
  SetRateActuatorControlTarget: MethodDefinition<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse, _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest__Output, _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>
  SetRateActuatorOutputStatus: MethodDefinition<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse, _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest__Output, _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>
  SetRateAltitude: MethodDefinition<_mavsdk_rpc_telemetry_SetRateAltitudeRequest, _mavsdk_rpc_telemetry_SetRateAltitudeResponse, _mavsdk_rpc_telemetry_SetRateAltitudeRequest__Output, _mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>
  SetRateAttitudeEuler: MethodDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse, _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest__Output, _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>
  SetRateAttitudeQuaternion: MethodDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse, _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest__Output, _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>
  SetRateBattery: MethodDefinition<_mavsdk_rpc_telemetry_SetRateBatteryRequest, _mavsdk_rpc_telemetry_SetRateBatteryResponse, _mavsdk_rpc_telemetry_SetRateBatteryRequest__Output, _mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>
  SetRateDistanceSensor: MethodDefinition<_mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse, _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest__Output, _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>
  SetRateFixedwingMetrics: MethodDefinition<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse, _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest__Output, _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>
  SetRateGpsInfo: MethodDefinition<_mavsdk_rpc_telemetry_SetRateGpsInfoRequest, _mavsdk_rpc_telemetry_SetRateGpsInfoResponse, _mavsdk_rpc_telemetry_SetRateGpsInfoRequest__Output, _mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>
  SetRateGroundTruth: MethodDefinition<_mavsdk_rpc_telemetry_SetRateGroundTruthRequest, _mavsdk_rpc_telemetry_SetRateGroundTruthResponse, _mavsdk_rpc_telemetry_SetRateGroundTruthRequest__Output, _mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>
  SetRateHealth: MethodDefinition<_mavsdk_rpc_telemetry_SetRateHealthRequest, _mavsdk_rpc_telemetry_SetRateHealthResponse, _mavsdk_rpc_telemetry_SetRateHealthRequest__Output, _mavsdk_rpc_telemetry_SetRateHealthResponse__Output>
  SetRateHome: MethodDefinition<_mavsdk_rpc_telemetry_SetRateHomeRequest, _mavsdk_rpc_telemetry_SetRateHomeResponse, _mavsdk_rpc_telemetry_SetRateHomeRequest__Output, _mavsdk_rpc_telemetry_SetRateHomeResponse__Output>
  SetRateImu: MethodDefinition<_mavsdk_rpc_telemetry_SetRateImuRequest, _mavsdk_rpc_telemetry_SetRateImuResponse, _mavsdk_rpc_telemetry_SetRateImuRequest__Output, _mavsdk_rpc_telemetry_SetRateImuResponse__Output>
  SetRateInAir: MethodDefinition<_mavsdk_rpc_telemetry_SetRateInAirRequest, _mavsdk_rpc_telemetry_SetRateInAirResponse, _mavsdk_rpc_telemetry_SetRateInAirRequest__Output, _mavsdk_rpc_telemetry_SetRateInAirResponse__Output>
  SetRateLandedState: MethodDefinition<_mavsdk_rpc_telemetry_SetRateLandedStateRequest, _mavsdk_rpc_telemetry_SetRateLandedStateResponse, _mavsdk_rpc_telemetry_SetRateLandedStateRequest__Output, _mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>
  SetRateOdometry: MethodDefinition<_mavsdk_rpc_telemetry_SetRateOdometryRequest, _mavsdk_rpc_telemetry_SetRateOdometryResponse, _mavsdk_rpc_telemetry_SetRateOdometryRequest__Output, _mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>
  SetRatePosition: MethodDefinition<_mavsdk_rpc_telemetry_SetRatePositionRequest, _mavsdk_rpc_telemetry_SetRatePositionResponse, _mavsdk_rpc_telemetry_SetRatePositionRequest__Output, _mavsdk_rpc_telemetry_SetRatePositionResponse__Output>
  SetRatePositionVelocityNed: MethodDefinition<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse, _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest__Output, _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>
  SetRateRawGps: MethodDefinition<_mavsdk_rpc_telemetry_SetRateRawGpsRequest, _mavsdk_rpc_telemetry_SetRateRawGpsResponse, _mavsdk_rpc_telemetry_SetRateRawGpsRequest__Output, _mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>
  SetRateRawImu: MethodDefinition<_mavsdk_rpc_telemetry_SetRateRawImuRequest, _mavsdk_rpc_telemetry_SetRateRawImuResponse, _mavsdk_rpc_telemetry_SetRateRawImuRequest__Output, _mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>
  SetRateRcStatus: MethodDefinition<_mavsdk_rpc_telemetry_SetRateRcStatusRequest, _mavsdk_rpc_telemetry_SetRateRcStatusResponse, _mavsdk_rpc_telemetry_SetRateRcStatusRequest__Output, _mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>
  SetRateScaledImu: MethodDefinition<_mavsdk_rpc_telemetry_SetRateScaledImuRequest, _mavsdk_rpc_telemetry_SetRateScaledImuResponse, _mavsdk_rpc_telemetry_SetRateScaledImuRequest__Output, _mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>
  SetRateUnixEpochTime: MethodDefinition<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse, _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest__Output, _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>
  SetRateVelocityNed: MethodDefinition<_mavsdk_rpc_telemetry_SetRateVelocityNedRequest, _mavsdk_rpc_telemetry_SetRateVelocityNedResponse, _mavsdk_rpc_telemetry_SetRateVelocityNedRequest__Output, _mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>
  SetRateVtolState: MethodDefinition<_mavsdk_rpc_telemetry_SetRateVtolStateRequest, _mavsdk_rpc_telemetry_SetRateVtolStateResponse, _mavsdk_rpc_telemetry_SetRateVtolStateRequest__Output, _mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>
  SubscribeActuatorControlTarget: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, _mavsdk_rpc_telemetry_ActuatorControlTargetResponse, _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest__Output, _mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output>
  SubscribeActuatorOutputStatus: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse, _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest__Output, _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output>
  SubscribeAltitude: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeAltitudeRequest, _mavsdk_rpc_telemetry_AltitudeResponse, _mavsdk_rpc_telemetry_SubscribeAltitudeRequest__Output, _mavsdk_rpc_telemetry_AltitudeResponse__Output>
  SubscribeArmed: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeArmedRequest, _mavsdk_rpc_telemetry_ArmedResponse, _mavsdk_rpc_telemetry_SubscribeArmedRequest__Output, _mavsdk_rpc_telemetry_ArmedResponse__Output>
  SubscribeAttitudeAngularVelocityBody: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse, _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest__Output, _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output>
  SubscribeAttitudeEuler: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, _mavsdk_rpc_telemetry_AttitudeEulerResponse, _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest__Output, _mavsdk_rpc_telemetry_AttitudeEulerResponse__Output>
  SubscribeAttitudeQuaternion: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, _mavsdk_rpc_telemetry_AttitudeQuaternionResponse, _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest__Output, _mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output>
  SubscribeBattery: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeBatteryRequest, _mavsdk_rpc_telemetry_BatteryResponse, _mavsdk_rpc_telemetry_SubscribeBatteryRequest__Output, _mavsdk_rpc_telemetry_BatteryResponse__Output>
  SubscribeDistanceSensor: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, _mavsdk_rpc_telemetry_DistanceSensorResponse, _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest__Output, _mavsdk_rpc_telemetry_DistanceSensorResponse__Output>
  SubscribeFixedwingMetrics: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, _mavsdk_rpc_telemetry_FixedwingMetricsResponse, _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest__Output, _mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output>
  SubscribeFlightMode: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeFlightModeRequest, _mavsdk_rpc_telemetry_FlightModeResponse, _mavsdk_rpc_telemetry_SubscribeFlightModeRequest__Output, _mavsdk_rpc_telemetry_FlightModeResponse__Output>
  SubscribeGpsInfo: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, _mavsdk_rpc_telemetry_GpsInfoResponse, _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest__Output, _mavsdk_rpc_telemetry_GpsInfoResponse__Output>
  SubscribeGroundTruth: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, _mavsdk_rpc_telemetry_GroundTruthResponse, _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest__Output, _mavsdk_rpc_telemetry_GroundTruthResponse__Output>
  SubscribeHeading: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeHeadingRequest, _mavsdk_rpc_telemetry_HeadingResponse, _mavsdk_rpc_telemetry_SubscribeHeadingRequest__Output, _mavsdk_rpc_telemetry_HeadingResponse__Output>
  SubscribeHealth: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeHealthRequest, _mavsdk_rpc_telemetry_HealthResponse, _mavsdk_rpc_telemetry_SubscribeHealthRequest__Output, _mavsdk_rpc_telemetry_HealthResponse__Output>
  SubscribeHealthAllOk: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, _mavsdk_rpc_telemetry_HealthAllOkResponse, _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest__Output, _mavsdk_rpc_telemetry_HealthAllOkResponse__Output>
  SubscribeHome: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeHomeRequest, _mavsdk_rpc_telemetry_HomeResponse, _mavsdk_rpc_telemetry_SubscribeHomeRequest__Output, _mavsdk_rpc_telemetry_HomeResponse__Output>
  SubscribeImu: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeImuRequest, _mavsdk_rpc_telemetry_ImuResponse, _mavsdk_rpc_telemetry_SubscribeImuRequest__Output, _mavsdk_rpc_telemetry_ImuResponse__Output>
  SubscribeInAir: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeInAirRequest, _mavsdk_rpc_telemetry_InAirResponse, _mavsdk_rpc_telemetry_SubscribeInAirRequest__Output, _mavsdk_rpc_telemetry_InAirResponse__Output>
  SubscribeLandedState: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeLandedStateRequest, _mavsdk_rpc_telemetry_LandedStateResponse, _mavsdk_rpc_telemetry_SubscribeLandedStateRequest__Output, _mavsdk_rpc_telemetry_LandedStateResponse__Output>
  SubscribeOdometry: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeOdometryRequest, _mavsdk_rpc_telemetry_OdometryResponse, _mavsdk_rpc_telemetry_SubscribeOdometryRequest__Output, _mavsdk_rpc_telemetry_OdometryResponse__Output>
  SubscribePosition: MethodDefinition<_mavsdk_rpc_telemetry_SubscribePositionRequest, _mavsdk_rpc_telemetry_PositionResponse, _mavsdk_rpc_telemetry_SubscribePositionRequest__Output, _mavsdk_rpc_telemetry_PositionResponse__Output>
  SubscribePositionVelocityNed: MethodDefinition<_mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, _mavsdk_rpc_telemetry_PositionVelocityNedResponse, _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest__Output, _mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output>
  SubscribeRawGps: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeRawGpsRequest, _mavsdk_rpc_telemetry_RawGpsResponse, _mavsdk_rpc_telemetry_SubscribeRawGpsRequest__Output, _mavsdk_rpc_telemetry_RawGpsResponse__Output>
  SubscribeRawImu: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeRawImuRequest, _mavsdk_rpc_telemetry_RawImuResponse, _mavsdk_rpc_telemetry_SubscribeRawImuRequest__Output, _mavsdk_rpc_telemetry_RawImuResponse__Output>
  SubscribeRcStatus: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeRcStatusRequest, _mavsdk_rpc_telemetry_RcStatusResponse, _mavsdk_rpc_telemetry_SubscribeRcStatusRequest__Output, _mavsdk_rpc_telemetry_RcStatusResponse__Output>
  SubscribeScaledImu: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeScaledImuRequest, _mavsdk_rpc_telemetry_ScaledImuResponse, _mavsdk_rpc_telemetry_SubscribeScaledImuRequest__Output, _mavsdk_rpc_telemetry_ScaledImuResponse__Output>
  SubscribeScaledPressure: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, _mavsdk_rpc_telemetry_ScaledPressureResponse, _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest__Output, _mavsdk_rpc_telemetry_ScaledPressureResponse__Output>
  SubscribeStatusText: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeStatusTextRequest, _mavsdk_rpc_telemetry_StatusTextResponse, _mavsdk_rpc_telemetry_SubscribeStatusTextRequest__Output, _mavsdk_rpc_telemetry_StatusTextResponse__Output>
  SubscribeUnixEpochTime: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, _mavsdk_rpc_telemetry_UnixEpochTimeResponse, _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest__Output, _mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output>
  SubscribeVelocityNed: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, _mavsdk_rpc_telemetry_VelocityNedResponse, _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest__Output, _mavsdk_rpc_telemetry_VelocityNedResponse__Output>
  SubscribeVtolState: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeVtolStateRequest, _mavsdk_rpc_telemetry_VtolStateResponse, _mavsdk_rpc_telemetry_SubscribeVtolStateRequest__Output, _mavsdk_rpc_telemetry_VtolStateResponse__Output>
  SubscribeWind: MethodDefinition<_mavsdk_rpc_telemetry_SubscribeWindRequest, _mavsdk_rpc_telemetry_WindResponse, _mavsdk_rpc_telemetry_SubscribeWindRequest__Output, _mavsdk_rpc_telemetry_WindResponse__Output>
}
