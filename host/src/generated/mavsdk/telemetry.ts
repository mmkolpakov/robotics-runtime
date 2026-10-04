import type * as grpc from '@grpc/grpc-js';
import type { EnumTypeDefinition, MessageTypeDefinition } from '@grpc/proto-loader';

import type { DescriptorProto as _google_protobuf_DescriptorProto, DescriptorProto__Output as _google_protobuf_DescriptorProto__Output } from './google/protobuf/DescriptorProto.js';
import type { EnumDescriptorProto as _google_protobuf_EnumDescriptorProto, EnumDescriptorProto__Output as _google_protobuf_EnumDescriptorProto__Output } from './google/protobuf/EnumDescriptorProto.js';
import type { EnumOptions as _google_protobuf_EnumOptions, EnumOptions__Output as _google_protobuf_EnumOptions__Output } from './google/protobuf/EnumOptions.js';
import type { EnumValueDescriptorProto as _google_protobuf_EnumValueDescriptorProto, EnumValueDescriptorProto__Output as _google_protobuf_EnumValueDescriptorProto__Output } from './google/protobuf/EnumValueDescriptorProto.js';
import type { EnumValueOptions as _google_protobuf_EnumValueOptions, EnumValueOptions__Output as _google_protobuf_EnumValueOptions__Output } from './google/protobuf/EnumValueOptions.js';
import type { ExtensionRangeOptions as _google_protobuf_ExtensionRangeOptions, ExtensionRangeOptions__Output as _google_protobuf_ExtensionRangeOptions__Output } from './google/protobuf/ExtensionRangeOptions.js';
import type { FeatureSet as _google_protobuf_FeatureSet, FeatureSet__Output as _google_protobuf_FeatureSet__Output } from './google/protobuf/FeatureSet.js';
import type { FeatureSetDefaults as _google_protobuf_FeatureSetDefaults, FeatureSetDefaults__Output as _google_protobuf_FeatureSetDefaults__Output } from './google/protobuf/FeatureSetDefaults.js';
import type { FieldDescriptorProto as _google_protobuf_FieldDescriptorProto, FieldDescriptorProto__Output as _google_protobuf_FieldDescriptorProto__Output } from './google/protobuf/FieldDescriptorProto.js';
import type { FieldOptions as _google_protobuf_FieldOptions, FieldOptions__Output as _google_protobuf_FieldOptions__Output } from './google/protobuf/FieldOptions.js';
import type { FileDescriptorProto as _google_protobuf_FileDescriptorProto, FileDescriptorProto__Output as _google_protobuf_FileDescriptorProto__Output } from './google/protobuf/FileDescriptorProto.js';
import type { FileDescriptorSet as _google_protobuf_FileDescriptorSet, FileDescriptorSet__Output as _google_protobuf_FileDescriptorSet__Output } from './google/protobuf/FileDescriptorSet.js';
import type { FileOptions as _google_protobuf_FileOptions, FileOptions__Output as _google_protobuf_FileOptions__Output } from './google/protobuf/FileOptions.js';
import type { GeneratedCodeInfo as _google_protobuf_GeneratedCodeInfo, GeneratedCodeInfo__Output as _google_protobuf_GeneratedCodeInfo__Output } from './google/protobuf/GeneratedCodeInfo.js';
import type { MessageOptions as _google_protobuf_MessageOptions, MessageOptions__Output as _google_protobuf_MessageOptions__Output } from './google/protobuf/MessageOptions.js';
import type { MethodDescriptorProto as _google_protobuf_MethodDescriptorProto, MethodDescriptorProto__Output as _google_protobuf_MethodDescriptorProto__Output } from './google/protobuf/MethodDescriptorProto.js';
import type { MethodOptions as _google_protobuf_MethodOptions, MethodOptions__Output as _google_protobuf_MethodOptions__Output } from './google/protobuf/MethodOptions.js';
import type { OneofDescriptorProto as _google_protobuf_OneofDescriptorProto, OneofDescriptorProto__Output as _google_protobuf_OneofDescriptorProto__Output } from './google/protobuf/OneofDescriptorProto.js';
import type { OneofOptions as _google_protobuf_OneofOptions, OneofOptions__Output as _google_protobuf_OneofOptions__Output } from './google/protobuf/OneofOptions.js';
import type { ServiceDescriptorProto as _google_protobuf_ServiceDescriptorProto, ServiceDescriptorProto__Output as _google_protobuf_ServiceDescriptorProto__Output } from './google/protobuf/ServiceDescriptorProto.js';
import type { ServiceOptions as _google_protobuf_ServiceOptions, ServiceOptions__Output as _google_protobuf_ServiceOptions__Output } from './google/protobuf/ServiceOptions.js';
import type { SourceCodeInfo as _google_protobuf_SourceCodeInfo, SourceCodeInfo__Output as _google_protobuf_SourceCodeInfo__Output } from './google/protobuf/SourceCodeInfo.js';
import type { UninterpretedOption as _google_protobuf_UninterpretedOption, UninterpretedOption__Output as _google_protobuf_UninterpretedOption__Output } from './google/protobuf/UninterpretedOption.js';
import type { AccelerationFrd as _mavsdk_rpc_telemetry_AccelerationFrd, AccelerationFrd__Output as _mavsdk_rpc_telemetry_AccelerationFrd__Output } from './mavsdk/rpc/telemetry/AccelerationFrd.js';
import type { ActuatorControlTarget as _mavsdk_rpc_telemetry_ActuatorControlTarget, ActuatorControlTarget__Output as _mavsdk_rpc_telemetry_ActuatorControlTarget__Output } from './mavsdk/rpc/telemetry/ActuatorControlTarget.js';
import type { ActuatorControlTargetResponse as _mavsdk_rpc_telemetry_ActuatorControlTargetResponse, ActuatorControlTargetResponse__Output as _mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output } from './mavsdk/rpc/telemetry/ActuatorControlTargetResponse.js';
import type { ActuatorOutputStatus as _mavsdk_rpc_telemetry_ActuatorOutputStatus, ActuatorOutputStatus__Output as _mavsdk_rpc_telemetry_ActuatorOutputStatus__Output } from './mavsdk/rpc/telemetry/ActuatorOutputStatus.js';
import type { ActuatorOutputStatusResponse as _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse, ActuatorOutputStatusResponse__Output as _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output } from './mavsdk/rpc/telemetry/ActuatorOutputStatusResponse.js';
import type { Altitude as _mavsdk_rpc_telemetry_Altitude, Altitude__Output as _mavsdk_rpc_telemetry_Altitude__Output } from './mavsdk/rpc/telemetry/Altitude.js';
import type { AltitudeResponse as _mavsdk_rpc_telemetry_AltitudeResponse, AltitudeResponse__Output as _mavsdk_rpc_telemetry_AltitudeResponse__Output } from './mavsdk/rpc/telemetry/AltitudeResponse.js';
import type { AngularVelocityBody as _mavsdk_rpc_telemetry_AngularVelocityBody, AngularVelocityBody__Output as _mavsdk_rpc_telemetry_AngularVelocityBody__Output } from './mavsdk/rpc/telemetry/AngularVelocityBody.js';
import type { AngularVelocityFrd as _mavsdk_rpc_telemetry_AngularVelocityFrd, AngularVelocityFrd__Output as _mavsdk_rpc_telemetry_AngularVelocityFrd__Output } from './mavsdk/rpc/telemetry/AngularVelocityFrd.js';
import type { ArmedResponse as _mavsdk_rpc_telemetry_ArmedResponse, ArmedResponse__Output as _mavsdk_rpc_telemetry_ArmedResponse__Output } from './mavsdk/rpc/telemetry/ArmedResponse.js';
import type { AttitudeAngularVelocityBodyResponse as _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse, AttitudeAngularVelocityBodyResponse__Output as _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output } from './mavsdk/rpc/telemetry/AttitudeAngularVelocityBodyResponse.js';
import type { AttitudeEulerResponse as _mavsdk_rpc_telemetry_AttitudeEulerResponse, AttitudeEulerResponse__Output as _mavsdk_rpc_telemetry_AttitudeEulerResponse__Output } from './mavsdk/rpc/telemetry/AttitudeEulerResponse.js';
import type { AttitudeQuaternionResponse as _mavsdk_rpc_telemetry_AttitudeQuaternionResponse, AttitudeQuaternionResponse__Output as _mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output } from './mavsdk/rpc/telemetry/AttitudeQuaternionResponse.js';
import type { Battery as _mavsdk_rpc_telemetry_Battery, Battery__Output as _mavsdk_rpc_telemetry_Battery__Output } from './mavsdk/rpc/telemetry/Battery.js';
import type { BatteryResponse as _mavsdk_rpc_telemetry_BatteryResponse, BatteryResponse__Output as _mavsdk_rpc_telemetry_BatteryResponse__Output } from './mavsdk/rpc/telemetry/BatteryResponse.js';
import type { Covariance as _mavsdk_rpc_telemetry_Covariance, Covariance__Output as _mavsdk_rpc_telemetry_Covariance__Output } from './mavsdk/rpc/telemetry/Covariance.js';
import type { DistanceSensor as _mavsdk_rpc_telemetry_DistanceSensor, DistanceSensor__Output as _mavsdk_rpc_telemetry_DistanceSensor__Output } from './mavsdk/rpc/telemetry/DistanceSensor.js';
import type { DistanceSensorResponse as _mavsdk_rpc_telemetry_DistanceSensorResponse, DistanceSensorResponse__Output as _mavsdk_rpc_telemetry_DistanceSensorResponse__Output } from './mavsdk/rpc/telemetry/DistanceSensorResponse.js';
import type { EulerAngle as _mavsdk_rpc_telemetry_EulerAngle, EulerAngle__Output as _mavsdk_rpc_telemetry_EulerAngle__Output } from './mavsdk/rpc/telemetry/EulerAngle.js';
import type { FixedwingMetrics as _mavsdk_rpc_telemetry_FixedwingMetrics, FixedwingMetrics__Output as _mavsdk_rpc_telemetry_FixedwingMetrics__Output } from './mavsdk/rpc/telemetry/FixedwingMetrics.js';
import type { FixedwingMetricsResponse as _mavsdk_rpc_telemetry_FixedwingMetricsResponse, FixedwingMetricsResponse__Output as _mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output } from './mavsdk/rpc/telemetry/FixedwingMetricsResponse.js';
import type { FlightModeResponse as _mavsdk_rpc_telemetry_FlightModeResponse, FlightModeResponse__Output as _mavsdk_rpc_telemetry_FlightModeResponse__Output } from './mavsdk/rpc/telemetry/FlightModeResponse.js';
import type { GetGpsGlobalOriginRequest as _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, GetGpsGlobalOriginRequest__Output as _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest__Output } from './mavsdk/rpc/telemetry/GetGpsGlobalOriginRequest.js';
import type { GetGpsGlobalOriginResponse as _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse, GetGpsGlobalOriginResponse__Output as _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output } from './mavsdk/rpc/telemetry/GetGpsGlobalOriginResponse.js';
import type { GpsGlobalOrigin as _mavsdk_rpc_telemetry_GpsGlobalOrigin, GpsGlobalOrigin__Output as _mavsdk_rpc_telemetry_GpsGlobalOrigin__Output } from './mavsdk/rpc/telemetry/GpsGlobalOrigin.js';
import type { GpsInfo as _mavsdk_rpc_telemetry_GpsInfo, GpsInfo__Output as _mavsdk_rpc_telemetry_GpsInfo__Output } from './mavsdk/rpc/telemetry/GpsInfo.js';
import type { GpsInfoResponse as _mavsdk_rpc_telemetry_GpsInfoResponse, GpsInfoResponse__Output as _mavsdk_rpc_telemetry_GpsInfoResponse__Output } from './mavsdk/rpc/telemetry/GpsInfoResponse.js';
import type { GroundTruth as _mavsdk_rpc_telemetry_GroundTruth, GroundTruth__Output as _mavsdk_rpc_telemetry_GroundTruth__Output } from './mavsdk/rpc/telemetry/GroundTruth.js';
import type { GroundTruthResponse as _mavsdk_rpc_telemetry_GroundTruthResponse, GroundTruthResponse__Output as _mavsdk_rpc_telemetry_GroundTruthResponse__Output } from './mavsdk/rpc/telemetry/GroundTruthResponse.js';
import type { Heading as _mavsdk_rpc_telemetry_Heading, Heading__Output as _mavsdk_rpc_telemetry_Heading__Output } from './mavsdk/rpc/telemetry/Heading.js';
import type { HeadingResponse as _mavsdk_rpc_telemetry_HeadingResponse, HeadingResponse__Output as _mavsdk_rpc_telemetry_HeadingResponse__Output } from './mavsdk/rpc/telemetry/HeadingResponse.js';
import type { Health as _mavsdk_rpc_telemetry_Health, Health__Output as _mavsdk_rpc_telemetry_Health__Output } from './mavsdk/rpc/telemetry/Health.js';
import type { HealthAllOkResponse as _mavsdk_rpc_telemetry_HealthAllOkResponse, HealthAllOkResponse__Output as _mavsdk_rpc_telemetry_HealthAllOkResponse__Output } from './mavsdk/rpc/telemetry/HealthAllOkResponse.js';
import type { HealthResponse as _mavsdk_rpc_telemetry_HealthResponse, HealthResponse__Output as _mavsdk_rpc_telemetry_HealthResponse__Output } from './mavsdk/rpc/telemetry/HealthResponse.js';
import type { HomePosition as _mavsdk_rpc_telemetry_HomePosition, HomePosition__Output as _mavsdk_rpc_telemetry_HomePosition__Output } from './mavsdk/rpc/telemetry/HomePosition.js';
import type { HomeResponse as _mavsdk_rpc_telemetry_HomeResponse, HomeResponse__Output as _mavsdk_rpc_telemetry_HomeResponse__Output } from './mavsdk/rpc/telemetry/HomeResponse.js';
import type { Imu as _mavsdk_rpc_telemetry_Imu, Imu__Output as _mavsdk_rpc_telemetry_Imu__Output } from './mavsdk/rpc/telemetry/Imu.js';
import type { ImuResponse as _mavsdk_rpc_telemetry_ImuResponse, ImuResponse__Output as _mavsdk_rpc_telemetry_ImuResponse__Output } from './mavsdk/rpc/telemetry/ImuResponse.js';
import type { InAirResponse as _mavsdk_rpc_telemetry_InAirResponse, InAirResponse__Output as _mavsdk_rpc_telemetry_InAirResponse__Output } from './mavsdk/rpc/telemetry/InAirResponse.js';
import type { LandedStateResponse as _mavsdk_rpc_telemetry_LandedStateResponse, LandedStateResponse__Output as _mavsdk_rpc_telemetry_LandedStateResponse__Output } from './mavsdk/rpc/telemetry/LandedStateResponse.js';
import type { MagneticFieldFrd as _mavsdk_rpc_telemetry_MagneticFieldFrd, MagneticFieldFrd__Output as _mavsdk_rpc_telemetry_MagneticFieldFrd__Output } from './mavsdk/rpc/telemetry/MagneticFieldFrd.js';
import type { Odometry as _mavsdk_rpc_telemetry_Odometry, Odometry__Output as _mavsdk_rpc_telemetry_Odometry__Output } from './mavsdk/rpc/telemetry/Odometry.js';
import type { OdometryResponse as _mavsdk_rpc_telemetry_OdometryResponse, OdometryResponse__Output as _mavsdk_rpc_telemetry_OdometryResponse__Output } from './mavsdk/rpc/telemetry/OdometryResponse.js';
import type { Position as _mavsdk_rpc_telemetry_Position, Position__Output as _mavsdk_rpc_telemetry_Position__Output } from './mavsdk/rpc/telemetry/Position.js';
import type { PositionBody as _mavsdk_rpc_telemetry_PositionBody, PositionBody__Output as _mavsdk_rpc_telemetry_PositionBody__Output } from './mavsdk/rpc/telemetry/PositionBody.js';
import type { PositionNed as _mavsdk_rpc_telemetry_PositionNed, PositionNed__Output as _mavsdk_rpc_telemetry_PositionNed__Output } from './mavsdk/rpc/telemetry/PositionNed.js';
import type { PositionResponse as _mavsdk_rpc_telemetry_PositionResponse, PositionResponse__Output as _mavsdk_rpc_telemetry_PositionResponse__Output } from './mavsdk/rpc/telemetry/PositionResponse.js';
import type { PositionVelocityNed as _mavsdk_rpc_telemetry_PositionVelocityNed, PositionVelocityNed__Output as _mavsdk_rpc_telemetry_PositionVelocityNed__Output } from './mavsdk/rpc/telemetry/PositionVelocityNed.js';
import type { PositionVelocityNedResponse as _mavsdk_rpc_telemetry_PositionVelocityNedResponse, PositionVelocityNedResponse__Output as _mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output } from './mavsdk/rpc/telemetry/PositionVelocityNedResponse.js';
import type { Quaternion as _mavsdk_rpc_telemetry_Quaternion, Quaternion__Output as _mavsdk_rpc_telemetry_Quaternion__Output } from './mavsdk/rpc/telemetry/Quaternion.js';
import type { RawGps as _mavsdk_rpc_telemetry_RawGps, RawGps__Output as _mavsdk_rpc_telemetry_RawGps__Output } from './mavsdk/rpc/telemetry/RawGps.js';
import type { RawGpsResponse as _mavsdk_rpc_telemetry_RawGpsResponse, RawGpsResponse__Output as _mavsdk_rpc_telemetry_RawGpsResponse__Output } from './mavsdk/rpc/telemetry/RawGpsResponse.js';
import type { RawImuResponse as _mavsdk_rpc_telemetry_RawImuResponse, RawImuResponse__Output as _mavsdk_rpc_telemetry_RawImuResponse__Output } from './mavsdk/rpc/telemetry/RawImuResponse.js';
import type { RcStatus as _mavsdk_rpc_telemetry_RcStatus, RcStatus__Output as _mavsdk_rpc_telemetry_RcStatus__Output } from './mavsdk/rpc/telemetry/RcStatus.js';
import type { RcStatusResponse as _mavsdk_rpc_telemetry_RcStatusResponse, RcStatusResponse__Output as _mavsdk_rpc_telemetry_RcStatusResponse__Output } from './mavsdk/rpc/telemetry/RcStatusResponse.js';
import type { ScaledImuResponse as _mavsdk_rpc_telemetry_ScaledImuResponse, ScaledImuResponse__Output as _mavsdk_rpc_telemetry_ScaledImuResponse__Output } from './mavsdk/rpc/telemetry/ScaledImuResponse.js';
import type { ScaledPressure as _mavsdk_rpc_telemetry_ScaledPressure, ScaledPressure__Output as _mavsdk_rpc_telemetry_ScaledPressure__Output } from './mavsdk/rpc/telemetry/ScaledPressure.js';
import type { ScaledPressureResponse as _mavsdk_rpc_telemetry_ScaledPressureResponse, ScaledPressureResponse__Output as _mavsdk_rpc_telemetry_ScaledPressureResponse__Output } from './mavsdk/rpc/telemetry/ScaledPressureResponse.js';
import type { SetRateActuatorControlTargetRequest as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, SetRateActuatorControlTargetRequest__Output as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest__Output } from './mavsdk/rpc/telemetry/SetRateActuatorControlTargetRequest.js';
import type { SetRateActuatorControlTargetResponse as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse, SetRateActuatorControlTargetResponse__Output as _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output } from './mavsdk/rpc/telemetry/SetRateActuatorControlTargetResponse.js';
import type { SetRateActuatorOutputStatusRequest as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, SetRateActuatorOutputStatusRequest__Output as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest__Output } from './mavsdk/rpc/telemetry/SetRateActuatorOutputStatusRequest.js';
import type { SetRateActuatorOutputStatusResponse as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse, SetRateActuatorOutputStatusResponse__Output as _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output } from './mavsdk/rpc/telemetry/SetRateActuatorOutputStatusResponse.js';
import type { SetRateAltitudeRequest as _mavsdk_rpc_telemetry_SetRateAltitudeRequest, SetRateAltitudeRequest__Output as _mavsdk_rpc_telemetry_SetRateAltitudeRequest__Output } from './mavsdk/rpc/telemetry/SetRateAltitudeRequest.js';
import type { SetRateAltitudeResponse as _mavsdk_rpc_telemetry_SetRateAltitudeResponse, SetRateAltitudeResponse__Output as _mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output } from './mavsdk/rpc/telemetry/SetRateAltitudeResponse.js';
import type { SetRateAttitudeAngularVelocityBodyRequest as _mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyRequest, SetRateAttitudeAngularVelocityBodyRequest__Output as _mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyRequest__Output } from './mavsdk/rpc/telemetry/SetRateAttitudeAngularVelocityBodyRequest.js';
import type { SetRateAttitudeAngularVelocityBodyResponse as _mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyResponse, SetRateAttitudeAngularVelocityBodyResponse__Output as _mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyResponse__Output } from './mavsdk/rpc/telemetry/SetRateAttitudeAngularVelocityBodyResponse.js';
import type { SetRateAttitudeEulerRequest as _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, SetRateAttitudeEulerRequest__Output as _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest__Output } from './mavsdk/rpc/telemetry/SetRateAttitudeEulerRequest.js';
import type { SetRateAttitudeEulerResponse as _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse, SetRateAttitudeEulerResponse__Output as _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output } from './mavsdk/rpc/telemetry/SetRateAttitudeEulerResponse.js';
import type { SetRateAttitudeQuaternionRequest as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, SetRateAttitudeQuaternionRequest__Output as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest__Output } from './mavsdk/rpc/telemetry/SetRateAttitudeQuaternionRequest.js';
import type { SetRateAttitudeQuaternionResponse as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse, SetRateAttitudeQuaternionResponse__Output as _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output } from './mavsdk/rpc/telemetry/SetRateAttitudeQuaternionResponse.js';
import type { SetRateBatteryRequest as _mavsdk_rpc_telemetry_SetRateBatteryRequest, SetRateBatteryRequest__Output as _mavsdk_rpc_telemetry_SetRateBatteryRequest__Output } from './mavsdk/rpc/telemetry/SetRateBatteryRequest.js';
import type { SetRateBatteryResponse as _mavsdk_rpc_telemetry_SetRateBatteryResponse, SetRateBatteryResponse__Output as _mavsdk_rpc_telemetry_SetRateBatteryResponse__Output } from './mavsdk/rpc/telemetry/SetRateBatteryResponse.js';
import type { SetRateDistanceSensorRequest as _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, SetRateDistanceSensorRequest__Output as _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest__Output } from './mavsdk/rpc/telemetry/SetRateDistanceSensorRequest.js';
import type { SetRateDistanceSensorResponse as _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse, SetRateDistanceSensorResponse__Output as _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output } from './mavsdk/rpc/telemetry/SetRateDistanceSensorResponse.js';
import type { SetRateFixedwingMetricsRequest as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, SetRateFixedwingMetricsRequest__Output as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest__Output } from './mavsdk/rpc/telemetry/SetRateFixedwingMetricsRequest.js';
import type { SetRateFixedwingMetricsResponse as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse, SetRateFixedwingMetricsResponse__Output as _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output } from './mavsdk/rpc/telemetry/SetRateFixedwingMetricsResponse.js';
import type { SetRateGpsInfoRequest as _mavsdk_rpc_telemetry_SetRateGpsInfoRequest, SetRateGpsInfoRequest__Output as _mavsdk_rpc_telemetry_SetRateGpsInfoRequest__Output } from './mavsdk/rpc/telemetry/SetRateGpsInfoRequest.js';
import type { SetRateGpsInfoResponse as _mavsdk_rpc_telemetry_SetRateGpsInfoResponse, SetRateGpsInfoResponse__Output as _mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output } from './mavsdk/rpc/telemetry/SetRateGpsInfoResponse.js';
import type { SetRateGroundTruthRequest as _mavsdk_rpc_telemetry_SetRateGroundTruthRequest, SetRateGroundTruthRequest__Output as _mavsdk_rpc_telemetry_SetRateGroundTruthRequest__Output } from './mavsdk/rpc/telemetry/SetRateGroundTruthRequest.js';
import type { SetRateGroundTruthResponse as _mavsdk_rpc_telemetry_SetRateGroundTruthResponse, SetRateGroundTruthResponse__Output as _mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output } from './mavsdk/rpc/telemetry/SetRateGroundTruthResponse.js';
import type { SetRateHealthRequest as _mavsdk_rpc_telemetry_SetRateHealthRequest, SetRateHealthRequest__Output as _mavsdk_rpc_telemetry_SetRateHealthRequest__Output } from './mavsdk/rpc/telemetry/SetRateHealthRequest.js';
import type { SetRateHealthResponse as _mavsdk_rpc_telemetry_SetRateHealthResponse, SetRateHealthResponse__Output as _mavsdk_rpc_telemetry_SetRateHealthResponse__Output } from './mavsdk/rpc/telemetry/SetRateHealthResponse.js';
import type { SetRateHomeRequest as _mavsdk_rpc_telemetry_SetRateHomeRequest, SetRateHomeRequest__Output as _mavsdk_rpc_telemetry_SetRateHomeRequest__Output } from './mavsdk/rpc/telemetry/SetRateHomeRequest.js';
import type { SetRateHomeResponse as _mavsdk_rpc_telemetry_SetRateHomeResponse, SetRateHomeResponse__Output as _mavsdk_rpc_telemetry_SetRateHomeResponse__Output } from './mavsdk/rpc/telemetry/SetRateHomeResponse.js';
import type { SetRateImuRequest as _mavsdk_rpc_telemetry_SetRateImuRequest, SetRateImuRequest__Output as _mavsdk_rpc_telemetry_SetRateImuRequest__Output } from './mavsdk/rpc/telemetry/SetRateImuRequest.js';
import type { SetRateImuResponse as _mavsdk_rpc_telemetry_SetRateImuResponse, SetRateImuResponse__Output as _mavsdk_rpc_telemetry_SetRateImuResponse__Output } from './mavsdk/rpc/telemetry/SetRateImuResponse.js';
import type { SetRateInAirRequest as _mavsdk_rpc_telemetry_SetRateInAirRequest, SetRateInAirRequest__Output as _mavsdk_rpc_telemetry_SetRateInAirRequest__Output } from './mavsdk/rpc/telemetry/SetRateInAirRequest.js';
import type { SetRateInAirResponse as _mavsdk_rpc_telemetry_SetRateInAirResponse, SetRateInAirResponse__Output as _mavsdk_rpc_telemetry_SetRateInAirResponse__Output } from './mavsdk/rpc/telemetry/SetRateInAirResponse.js';
import type { SetRateLandedStateRequest as _mavsdk_rpc_telemetry_SetRateLandedStateRequest, SetRateLandedStateRequest__Output as _mavsdk_rpc_telemetry_SetRateLandedStateRequest__Output } from './mavsdk/rpc/telemetry/SetRateLandedStateRequest.js';
import type { SetRateLandedStateResponse as _mavsdk_rpc_telemetry_SetRateLandedStateResponse, SetRateLandedStateResponse__Output as _mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output } from './mavsdk/rpc/telemetry/SetRateLandedStateResponse.js';
import type { SetRateOdometryRequest as _mavsdk_rpc_telemetry_SetRateOdometryRequest, SetRateOdometryRequest__Output as _mavsdk_rpc_telemetry_SetRateOdometryRequest__Output } from './mavsdk/rpc/telemetry/SetRateOdometryRequest.js';
import type { SetRateOdometryResponse as _mavsdk_rpc_telemetry_SetRateOdometryResponse, SetRateOdometryResponse__Output as _mavsdk_rpc_telemetry_SetRateOdometryResponse__Output } from './mavsdk/rpc/telemetry/SetRateOdometryResponse.js';
import type { SetRatePositionRequest as _mavsdk_rpc_telemetry_SetRatePositionRequest, SetRatePositionRequest__Output as _mavsdk_rpc_telemetry_SetRatePositionRequest__Output } from './mavsdk/rpc/telemetry/SetRatePositionRequest.js';
import type { SetRatePositionResponse as _mavsdk_rpc_telemetry_SetRatePositionResponse, SetRatePositionResponse__Output as _mavsdk_rpc_telemetry_SetRatePositionResponse__Output } from './mavsdk/rpc/telemetry/SetRatePositionResponse.js';
import type { SetRatePositionVelocityNedRequest as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, SetRatePositionVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest__Output } from './mavsdk/rpc/telemetry/SetRatePositionVelocityNedRequest.js';
import type { SetRatePositionVelocityNedResponse as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse, SetRatePositionVelocityNedResponse__Output as _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output } from './mavsdk/rpc/telemetry/SetRatePositionVelocityNedResponse.js';
import type { SetRateRawGpsRequest as _mavsdk_rpc_telemetry_SetRateRawGpsRequest, SetRateRawGpsRequest__Output as _mavsdk_rpc_telemetry_SetRateRawGpsRequest__Output } from './mavsdk/rpc/telemetry/SetRateRawGpsRequest.js';
import type { SetRateRawGpsResponse as _mavsdk_rpc_telemetry_SetRateRawGpsResponse, SetRateRawGpsResponse__Output as _mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output } from './mavsdk/rpc/telemetry/SetRateRawGpsResponse.js';
import type { SetRateRawImuRequest as _mavsdk_rpc_telemetry_SetRateRawImuRequest, SetRateRawImuRequest__Output as _mavsdk_rpc_telemetry_SetRateRawImuRequest__Output } from './mavsdk/rpc/telemetry/SetRateRawImuRequest.js';
import type { SetRateRawImuResponse as _mavsdk_rpc_telemetry_SetRateRawImuResponse, SetRateRawImuResponse__Output as _mavsdk_rpc_telemetry_SetRateRawImuResponse__Output } from './mavsdk/rpc/telemetry/SetRateRawImuResponse.js';
import type { SetRateRcStatusRequest as _mavsdk_rpc_telemetry_SetRateRcStatusRequest, SetRateRcStatusRequest__Output as _mavsdk_rpc_telemetry_SetRateRcStatusRequest__Output } from './mavsdk/rpc/telemetry/SetRateRcStatusRequest.js';
import type { SetRateRcStatusResponse as _mavsdk_rpc_telemetry_SetRateRcStatusResponse, SetRateRcStatusResponse__Output as _mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output } from './mavsdk/rpc/telemetry/SetRateRcStatusResponse.js';
import type { SetRateScaledImuRequest as _mavsdk_rpc_telemetry_SetRateScaledImuRequest, SetRateScaledImuRequest__Output as _mavsdk_rpc_telemetry_SetRateScaledImuRequest__Output } from './mavsdk/rpc/telemetry/SetRateScaledImuRequest.js';
import type { SetRateScaledImuResponse as _mavsdk_rpc_telemetry_SetRateScaledImuResponse, SetRateScaledImuResponse__Output as _mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output } from './mavsdk/rpc/telemetry/SetRateScaledImuResponse.js';
import type { SetRateUnixEpochTimeRequest as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, SetRateUnixEpochTimeRequest__Output as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest__Output } from './mavsdk/rpc/telemetry/SetRateUnixEpochTimeRequest.js';
import type { SetRateUnixEpochTimeResponse as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse, SetRateUnixEpochTimeResponse__Output as _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output } from './mavsdk/rpc/telemetry/SetRateUnixEpochTimeResponse.js';
import type { SetRateVelocityNedRequest as _mavsdk_rpc_telemetry_SetRateVelocityNedRequest, SetRateVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SetRateVelocityNedRequest__Output } from './mavsdk/rpc/telemetry/SetRateVelocityNedRequest.js';
import type { SetRateVelocityNedResponse as _mavsdk_rpc_telemetry_SetRateVelocityNedResponse, SetRateVelocityNedResponse__Output as _mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output } from './mavsdk/rpc/telemetry/SetRateVelocityNedResponse.js';
import type { SetRateVtolStateRequest as _mavsdk_rpc_telemetry_SetRateVtolStateRequest, SetRateVtolStateRequest__Output as _mavsdk_rpc_telemetry_SetRateVtolStateRequest__Output } from './mavsdk/rpc/telemetry/SetRateVtolStateRequest.js';
import type { SetRateVtolStateResponse as _mavsdk_rpc_telemetry_SetRateVtolStateResponse, SetRateVtolStateResponse__Output as _mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output } from './mavsdk/rpc/telemetry/SetRateVtolStateResponse.js';
import type { StatusText as _mavsdk_rpc_telemetry_StatusText, StatusText__Output as _mavsdk_rpc_telemetry_StatusText__Output } from './mavsdk/rpc/telemetry/StatusText.js';
import type { StatusTextResponse as _mavsdk_rpc_telemetry_StatusTextResponse, StatusTextResponse__Output as _mavsdk_rpc_telemetry_StatusTextResponse__Output } from './mavsdk/rpc/telemetry/StatusTextResponse.js';
import type { SubscribeActuatorControlTargetRequest as _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, SubscribeActuatorControlTargetRequest__Output as _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest__Output } from './mavsdk/rpc/telemetry/SubscribeActuatorControlTargetRequest.js';
import type { SubscribeActuatorOutputStatusRequest as _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, SubscribeActuatorOutputStatusRequest__Output as _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest__Output } from './mavsdk/rpc/telemetry/SubscribeActuatorOutputStatusRequest.js';
import type { SubscribeAltitudeRequest as _mavsdk_rpc_telemetry_SubscribeAltitudeRequest, SubscribeAltitudeRequest__Output as _mavsdk_rpc_telemetry_SubscribeAltitudeRequest__Output } from './mavsdk/rpc/telemetry/SubscribeAltitudeRequest.js';
import type { SubscribeArmedRequest as _mavsdk_rpc_telemetry_SubscribeArmedRequest, SubscribeArmedRequest__Output as _mavsdk_rpc_telemetry_SubscribeArmedRequest__Output } from './mavsdk/rpc/telemetry/SubscribeArmedRequest.js';
import type { SubscribeAttitudeAngularVelocityBodyRequest as _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, SubscribeAttitudeAngularVelocityBodyRequest__Output as _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest__Output } from './mavsdk/rpc/telemetry/SubscribeAttitudeAngularVelocityBodyRequest.js';
import type { SubscribeAttitudeEulerRequest as _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, SubscribeAttitudeEulerRequest__Output as _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest__Output } from './mavsdk/rpc/telemetry/SubscribeAttitudeEulerRequest.js';
import type { SubscribeAttitudeQuaternionRequest as _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, SubscribeAttitudeQuaternionRequest__Output as _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest__Output } from './mavsdk/rpc/telemetry/SubscribeAttitudeQuaternionRequest.js';
import type { SubscribeBatteryRequest as _mavsdk_rpc_telemetry_SubscribeBatteryRequest, SubscribeBatteryRequest__Output as _mavsdk_rpc_telemetry_SubscribeBatteryRequest__Output } from './mavsdk/rpc/telemetry/SubscribeBatteryRequest.js';
import type { SubscribeDistanceSensorRequest as _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, SubscribeDistanceSensorRequest__Output as _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest__Output } from './mavsdk/rpc/telemetry/SubscribeDistanceSensorRequest.js';
import type { SubscribeFixedwingMetricsRequest as _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, SubscribeFixedwingMetricsRequest__Output as _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest__Output } from './mavsdk/rpc/telemetry/SubscribeFixedwingMetricsRequest.js';
import type { SubscribeFlightModeRequest as _mavsdk_rpc_telemetry_SubscribeFlightModeRequest, SubscribeFlightModeRequest__Output as _mavsdk_rpc_telemetry_SubscribeFlightModeRequest__Output } from './mavsdk/rpc/telemetry/SubscribeFlightModeRequest.js';
import type { SubscribeGpsInfoRequest as _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, SubscribeGpsInfoRequest__Output as _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest__Output } from './mavsdk/rpc/telemetry/SubscribeGpsInfoRequest.js';
import type { SubscribeGroundTruthRequest as _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, SubscribeGroundTruthRequest__Output as _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest__Output } from './mavsdk/rpc/telemetry/SubscribeGroundTruthRequest.js';
import type { SubscribeHeadingRequest as _mavsdk_rpc_telemetry_SubscribeHeadingRequest, SubscribeHeadingRequest__Output as _mavsdk_rpc_telemetry_SubscribeHeadingRequest__Output } from './mavsdk/rpc/telemetry/SubscribeHeadingRequest.js';
import type { SubscribeHealthAllOkRequest as _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, SubscribeHealthAllOkRequest__Output as _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest__Output } from './mavsdk/rpc/telemetry/SubscribeHealthAllOkRequest.js';
import type { SubscribeHealthRequest as _mavsdk_rpc_telemetry_SubscribeHealthRequest, SubscribeHealthRequest__Output as _mavsdk_rpc_telemetry_SubscribeHealthRequest__Output } from './mavsdk/rpc/telemetry/SubscribeHealthRequest.js';
import type { SubscribeHomeRequest as _mavsdk_rpc_telemetry_SubscribeHomeRequest, SubscribeHomeRequest__Output as _mavsdk_rpc_telemetry_SubscribeHomeRequest__Output } from './mavsdk/rpc/telemetry/SubscribeHomeRequest.js';
import type { SubscribeImuRequest as _mavsdk_rpc_telemetry_SubscribeImuRequest, SubscribeImuRequest__Output as _mavsdk_rpc_telemetry_SubscribeImuRequest__Output } from './mavsdk/rpc/telemetry/SubscribeImuRequest.js';
import type { SubscribeInAirRequest as _mavsdk_rpc_telemetry_SubscribeInAirRequest, SubscribeInAirRequest__Output as _mavsdk_rpc_telemetry_SubscribeInAirRequest__Output } from './mavsdk/rpc/telemetry/SubscribeInAirRequest.js';
import type { SubscribeLandedStateRequest as _mavsdk_rpc_telemetry_SubscribeLandedStateRequest, SubscribeLandedStateRequest__Output as _mavsdk_rpc_telemetry_SubscribeLandedStateRequest__Output } from './mavsdk/rpc/telemetry/SubscribeLandedStateRequest.js';
import type { SubscribeOdometryRequest as _mavsdk_rpc_telemetry_SubscribeOdometryRequest, SubscribeOdometryRequest__Output as _mavsdk_rpc_telemetry_SubscribeOdometryRequest__Output } from './mavsdk/rpc/telemetry/SubscribeOdometryRequest.js';
import type { SubscribePositionRequest as _mavsdk_rpc_telemetry_SubscribePositionRequest, SubscribePositionRequest__Output as _mavsdk_rpc_telemetry_SubscribePositionRequest__Output } from './mavsdk/rpc/telemetry/SubscribePositionRequest.js';
import type { SubscribePositionVelocityNedRequest as _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, SubscribePositionVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest__Output } from './mavsdk/rpc/telemetry/SubscribePositionVelocityNedRequest.js';
import type { SubscribeRawGpsRequest as _mavsdk_rpc_telemetry_SubscribeRawGpsRequest, SubscribeRawGpsRequest__Output as _mavsdk_rpc_telemetry_SubscribeRawGpsRequest__Output } from './mavsdk/rpc/telemetry/SubscribeRawGpsRequest.js';
import type { SubscribeRawImuRequest as _mavsdk_rpc_telemetry_SubscribeRawImuRequest, SubscribeRawImuRequest__Output as _mavsdk_rpc_telemetry_SubscribeRawImuRequest__Output } from './mavsdk/rpc/telemetry/SubscribeRawImuRequest.js';
import type { SubscribeRcStatusRequest as _mavsdk_rpc_telemetry_SubscribeRcStatusRequest, SubscribeRcStatusRequest__Output as _mavsdk_rpc_telemetry_SubscribeRcStatusRequest__Output } from './mavsdk/rpc/telemetry/SubscribeRcStatusRequest.js';
import type { SubscribeScaledImuRequest as _mavsdk_rpc_telemetry_SubscribeScaledImuRequest, SubscribeScaledImuRequest__Output as _mavsdk_rpc_telemetry_SubscribeScaledImuRequest__Output } from './mavsdk/rpc/telemetry/SubscribeScaledImuRequest.js';
import type { SubscribeScaledPressureRequest as _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, SubscribeScaledPressureRequest__Output as _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest__Output } from './mavsdk/rpc/telemetry/SubscribeScaledPressureRequest.js';
import type { SubscribeStatusTextRequest as _mavsdk_rpc_telemetry_SubscribeStatusTextRequest, SubscribeStatusTextRequest__Output as _mavsdk_rpc_telemetry_SubscribeStatusTextRequest__Output } from './mavsdk/rpc/telemetry/SubscribeStatusTextRequest.js';
import type { SubscribeUnixEpochTimeRequest as _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, SubscribeUnixEpochTimeRequest__Output as _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest__Output } from './mavsdk/rpc/telemetry/SubscribeUnixEpochTimeRequest.js';
import type { SubscribeVelocityNedRequest as _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, SubscribeVelocityNedRequest__Output as _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest__Output } from './mavsdk/rpc/telemetry/SubscribeVelocityNedRequest.js';
import type { SubscribeVtolStateRequest as _mavsdk_rpc_telemetry_SubscribeVtolStateRequest, SubscribeVtolStateRequest__Output as _mavsdk_rpc_telemetry_SubscribeVtolStateRequest__Output } from './mavsdk/rpc/telemetry/SubscribeVtolStateRequest.js';
import type { SubscribeWindRequest as _mavsdk_rpc_telemetry_SubscribeWindRequest, SubscribeWindRequest__Output as _mavsdk_rpc_telemetry_SubscribeWindRequest__Output } from './mavsdk/rpc/telemetry/SubscribeWindRequest.js';
import type { TelemetryResult as _mavsdk_rpc_telemetry_TelemetryResult, TelemetryResult__Output as _mavsdk_rpc_telemetry_TelemetryResult__Output } from './mavsdk/rpc/telemetry/TelemetryResult.js';
import type { TelemetryServiceClient as _mavsdk_rpc_telemetry_TelemetryServiceClient, TelemetryServiceDefinition as _mavsdk_rpc_telemetry_TelemetryServiceDefinition } from './mavsdk/rpc/telemetry/TelemetryService.js';
import type { UnixEpochTimeResponse as _mavsdk_rpc_telemetry_UnixEpochTimeResponse, UnixEpochTimeResponse__Output as _mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output } from './mavsdk/rpc/telemetry/UnixEpochTimeResponse.js';
import type { VelocityBody as _mavsdk_rpc_telemetry_VelocityBody, VelocityBody__Output as _mavsdk_rpc_telemetry_VelocityBody__Output } from './mavsdk/rpc/telemetry/VelocityBody.js';
import type { VelocityNed as _mavsdk_rpc_telemetry_VelocityNed, VelocityNed__Output as _mavsdk_rpc_telemetry_VelocityNed__Output } from './mavsdk/rpc/telemetry/VelocityNed.js';
import type { VelocityNedResponse as _mavsdk_rpc_telemetry_VelocityNedResponse, VelocityNedResponse__Output as _mavsdk_rpc_telemetry_VelocityNedResponse__Output } from './mavsdk/rpc/telemetry/VelocityNedResponse.js';
import type { VtolStateResponse as _mavsdk_rpc_telemetry_VtolStateResponse, VtolStateResponse__Output as _mavsdk_rpc_telemetry_VtolStateResponse__Output } from './mavsdk/rpc/telemetry/VtolStateResponse.js';
import type { Wind as _mavsdk_rpc_telemetry_Wind, Wind__Output as _mavsdk_rpc_telemetry_Wind__Output } from './mavsdk/rpc/telemetry/Wind.js';
import type { WindResponse as _mavsdk_rpc_telemetry_WindResponse, WindResponse__Output as _mavsdk_rpc_telemetry_WindResponse__Output } from './mavsdk/rpc/telemetry/WindResponse.js';

type SubtypeConstructor<Constructor extends new (...args: any) => any, Subtype> = {
  new(...args: ConstructorParameters<Constructor>): Subtype;
};

export interface ProtoGrpcType {
  google: {
    protobuf: {
      DescriptorProto: MessageTypeDefinition<_google_protobuf_DescriptorProto, _google_protobuf_DescriptorProto__Output>
      Edition: EnumTypeDefinition
      EnumDescriptorProto: MessageTypeDefinition<_google_protobuf_EnumDescriptorProto, _google_protobuf_EnumDescriptorProto__Output>
      EnumOptions: MessageTypeDefinition<_google_protobuf_EnumOptions, _google_protobuf_EnumOptions__Output>
      EnumValueDescriptorProto: MessageTypeDefinition<_google_protobuf_EnumValueDescriptorProto, _google_protobuf_EnumValueDescriptorProto__Output>
      EnumValueOptions: MessageTypeDefinition<_google_protobuf_EnumValueOptions, _google_protobuf_EnumValueOptions__Output>
      ExtensionRangeOptions: MessageTypeDefinition<_google_protobuf_ExtensionRangeOptions, _google_protobuf_ExtensionRangeOptions__Output>
      FeatureSet: MessageTypeDefinition<_google_protobuf_FeatureSet, _google_protobuf_FeatureSet__Output>
      FeatureSetDefaults: MessageTypeDefinition<_google_protobuf_FeatureSetDefaults, _google_protobuf_FeatureSetDefaults__Output>
      FieldDescriptorProto: MessageTypeDefinition<_google_protobuf_FieldDescriptorProto, _google_protobuf_FieldDescriptorProto__Output>
      FieldOptions: MessageTypeDefinition<_google_protobuf_FieldOptions, _google_protobuf_FieldOptions__Output>
      FileDescriptorProto: MessageTypeDefinition<_google_protobuf_FileDescriptorProto, _google_protobuf_FileDescriptorProto__Output>
      FileDescriptorSet: MessageTypeDefinition<_google_protobuf_FileDescriptorSet, _google_protobuf_FileDescriptorSet__Output>
      FileOptions: MessageTypeDefinition<_google_protobuf_FileOptions, _google_protobuf_FileOptions__Output>
      GeneratedCodeInfo: MessageTypeDefinition<_google_protobuf_GeneratedCodeInfo, _google_protobuf_GeneratedCodeInfo__Output>
      MessageOptions: MessageTypeDefinition<_google_protobuf_MessageOptions, _google_protobuf_MessageOptions__Output>
      MethodDescriptorProto: MessageTypeDefinition<_google_protobuf_MethodDescriptorProto, _google_protobuf_MethodDescriptorProto__Output>
      MethodOptions: MessageTypeDefinition<_google_protobuf_MethodOptions, _google_protobuf_MethodOptions__Output>
      OneofDescriptorProto: MessageTypeDefinition<_google_protobuf_OneofDescriptorProto, _google_protobuf_OneofDescriptorProto__Output>
      OneofOptions: MessageTypeDefinition<_google_protobuf_OneofOptions, _google_protobuf_OneofOptions__Output>
      ServiceDescriptorProto: MessageTypeDefinition<_google_protobuf_ServiceDescriptorProto, _google_protobuf_ServiceDescriptorProto__Output>
      ServiceOptions: MessageTypeDefinition<_google_protobuf_ServiceOptions, _google_protobuf_ServiceOptions__Output>
      SourceCodeInfo: MessageTypeDefinition<_google_protobuf_SourceCodeInfo, _google_protobuf_SourceCodeInfo__Output>
      SymbolVisibility: EnumTypeDefinition
      UninterpretedOption: MessageTypeDefinition<_google_protobuf_UninterpretedOption, _google_protobuf_UninterpretedOption__Output>
    }
  }
  mavsdk: {
    options: {
      AsyncType: EnumTypeDefinition
    }
    rpc: {
      telemetry: {
        AccelerationFrd: MessageTypeDefinition<_mavsdk_rpc_telemetry_AccelerationFrd, _mavsdk_rpc_telemetry_AccelerationFrd__Output>
        ActuatorControlTarget: MessageTypeDefinition<_mavsdk_rpc_telemetry_ActuatorControlTarget, _mavsdk_rpc_telemetry_ActuatorControlTarget__Output>
        ActuatorControlTargetResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_ActuatorControlTargetResponse, _mavsdk_rpc_telemetry_ActuatorControlTargetResponse__Output>
        ActuatorOutputStatus: MessageTypeDefinition<_mavsdk_rpc_telemetry_ActuatorOutputStatus, _mavsdk_rpc_telemetry_ActuatorOutputStatus__Output>
        ActuatorOutputStatusResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_ActuatorOutputStatusResponse, _mavsdk_rpc_telemetry_ActuatorOutputStatusResponse__Output>
        Altitude: MessageTypeDefinition<_mavsdk_rpc_telemetry_Altitude, _mavsdk_rpc_telemetry_Altitude__Output>
        AltitudeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_AltitudeResponse, _mavsdk_rpc_telemetry_AltitudeResponse__Output>
        AngularVelocityBody: MessageTypeDefinition<_mavsdk_rpc_telemetry_AngularVelocityBody, _mavsdk_rpc_telemetry_AngularVelocityBody__Output>
        AngularVelocityFrd: MessageTypeDefinition<_mavsdk_rpc_telemetry_AngularVelocityFrd, _mavsdk_rpc_telemetry_AngularVelocityFrd__Output>
        ArmedResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_ArmedResponse, _mavsdk_rpc_telemetry_ArmedResponse__Output>
        AttitudeAngularVelocityBodyResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse, _mavsdk_rpc_telemetry_AttitudeAngularVelocityBodyResponse__Output>
        AttitudeEulerResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_AttitudeEulerResponse, _mavsdk_rpc_telemetry_AttitudeEulerResponse__Output>
        AttitudeQuaternionResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_AttitudeQuaternionResponse, _mavsdk_rpc_telemetry_AttitudeQuaternionResponse__Output>
        Battery: MessageTypeDefinition<_mavsdk_rpc_telemetry_Battery, _mavsdk_rpc_telemetry_Battery__Output>
        BatteryFunction: EnumTypeDefinition
        BatteryResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_BatteryResponse, _mavsdk_rpc_telemetry_BatteryResponse__Output>
        Covariance: MessageTypeDefinition<_mavsdk_rpc_telemetry_Covariance, _mavsdk_rpc_telemetry_Covariance__Output>
        DistanceSensor: MessageTypeDefinition<_mavsdk_rpc_telemetry_DistanceSensor, _mavsdk_rpc_telemetry_DistanceSensor__Output>
        DistanceSensorResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_DistanceSensorResponse, _mavsdk_rpc_telemetry_DistanceSensorResponse__Output>
        EulerAngle: MessageTypeDefinition<_mavsdk_rpc_telemetry_EulerAngle, _mavsdk_rpc_telemetry_EulerAngle__Output>
        FixType: EnumTypeDefinition
        FixedwingMetrics: MessageTypeDefinition<_mavsdk_rpc_telemetry_FixedwingMetrics, _mavsdk_rpc_telemetry_FixedwingMetrics__Output>
        FixedwingMetricsResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_FixedwingMetricsResponse, _mavsdk_rpc_telemetry_FixedwingMetricsResponse__Output>
        FlightMode: EnumTypeDefinition
        FlightModeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_FlightModeResponse, _mavsdk_rpc_telemetry_FlightModeResponse__Output>
        GetGpsGlobalOriginRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest, _mavsdk_rpc_telemetry_GetGpsGlobalOriginRequest__Output>
        GetGpsGlobalOriginResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse, _mavsdk_rpc_telemetry_GetGpsGlobalOriginResponse__Output>
        GpsGlobalOrigin: MessageTypeDefinition<_mavsdk_rpc_telemetry_GpsGlobalOrigin, _mavsdk_rpc_telemetry_GpsGlobalOrigin__Output>
        GpsInfo: MessageTypeDefinition<_mavsdk_rpc_telemetry_GpsInfo, _mavsdk_rpc_telemetry_GpsInfo__Output>
        GpsInfoResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_GpsInfoResponse, _mavsdk_rpc_telemetry_GpsInfoResponse__Output>
        GroundTruth: MessageTypeDefinition<_mavsdk_rpc_telemetry_GroundTruth, _mavsdk_rpc_telemetry_GroundTruth__Output>
        GroundTruthResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_GroundTruthResponse, _mavsdk_rpc_telemetry_GroundTruthResponse__Output>
        Heading: MessageTypeDefinition<_mavsdk_rpc_telemetry_Heading, _mavsdk_rpc_telemetry_Heading__Output>
        HeadingResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_HeadingResponse, _mavsdk_rpc_telemetry_HeadingResponse__Output>
        Health: MessageTypeDefinition<_mavsdk_rpc_telemetry_Health, _mavsdk_rpc_telemetry_Health__Output>
        HealthAllOkResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_HealthAllOkResponse, _mavsdk_rpc_telemetry_HealthAllOkResponse__Output>
        HealthResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_HealthResponse, _mavsdk_rpc_telemetry_HealthResponse__Output>
        HomePosition: MessageTypeDefinition<_mavsdk_rpc_telemetry_HomePosition, _mavsdk_rpc_telemetry_HomePosition__Output>
        HomeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_HomeResponse, _mavsdk_rpc_telemetry_HomeResponse__Output>
        Imu: MessageTypeDefinition<_mavsdk_rpc_telemetry_Imu, _mavsdk_rpc_telemetry_Imu__Output>
        ImuResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_ImuResponse, _mavsdk_rpc_telemetry_ImuResponse__Output>
        InAirResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_InAirResponse, _mavsdk_rpc_telemetry_InAirResponse__Output>
        LandedState: EnumTypeDefinition
        LandedStateResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_LandedStateResponse, _mavsdk_rpc_telemetry_LandedStateResponse__Output>
        MagneticFieldFrd: MessageTypeDefinition<_mavsdk_rpc_telemetry_MagneticFieldFrd, _mavsdk_rpc_telemetry_MagneticFieldFrd__Output>
        Odometry: MessageTypeDefinition<_mavsdk_rpc_telemetry_Odometry, _mavsdk_rpc_telemetry_Odometry__Output>
        OdometryResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_OdometryResponse, _mavsdk_rpc_telemetry_OdometryResponse__Output>
        Position: MessageTypeDefinition<_mavsdk_rpc_telemetry_Position, _mavsdk_rpc_telemetry_Position__Output>
        PositionBody: MessageTypeDefinition<_mavsdk_rpc_telemetry_PositionBody, _mavsdk_rpc_telemetry_PositionBody__Output>
        PositionNed: MessageTypeDefinition<_mavsdk_rpc_telemetry_PositionNed, _mavsdk_rpc_telemetry_PositionNed__Output>
        PositionResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_PositionResponse, _mavsdk_rpc_telemetry_PositionResponse__Output>
        PositionVelocityNed: MessageTypeDefinition<_mavsdk_rpc_telemetry_PositionVelocityNed, _mavsdk_rpc_telemetry_PositionVelocityNed__Output>
        PositionVelocityNedResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_PositionVelocityNedResponse, _mavsdk_rpc_telemetry_PositionVelocityNedResponse__Output>
        Quaternion: MessageTypeDefinition<_mavsdk_rpc_telemetry_Quaternion, _mavsdk_rpc_telemetry_Quaternion__Output>
        RawGps: MessageTypeDefinition<_mavsdk_rpc_telemetry_RawGps, _mavsdk_rpc_telemetry_RawGps__Output>
        RawGpsResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_RawGpsResponse, _mavsdk_rpc_telemetry_RawGpsResponse__Output>
        RawImuResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_RawImuResponse, _mavsdk_rpc_telemetry_RawImuResponse__Output>
        RcStatus: MessageTypeDefinition<_mavsdk_rpc_telemetry_RcStatus, _mavsdk_rpc_telemetry_RcStatus__Output>
        RcStatusResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_RcStatusResponse, _mavsdk_rpc_telemetry_RcStatusResponse__Output>
        ScaledImuResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_ScaledImuResponse, _mavsdk_rpc_telemetry_ScaledImuResponse__Output>
        ScaledPressure: MessageTypeDefinition<_mavsdk_rpc_telemetry_ScaledPressure, _mavsdk_rpc_telemetry_ScaledPressure__Output>
        ScaledPressureResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_ScaledPressureResponse, _mavsdk_rpc_telemetry_ScaledPressureResponse__Output>
        SetRateActuatorControlTargetRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest, _mavsdk_rpc_telemetry_SetRateActuatorControlTargetRequest__Output>
        SetRateActuatorControlTargetResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse, _mavsdk_rpc_telemetry_SetRateActuatorControlTargetResponse__Output>
        SetRateActuatorOutputStatusRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest, _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusRequest__Output>
        SetRateActuatorOutputStatusResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse, _mavsdk_rpc_telemetry_SetRateActuatorOutputStatusResponse__Output>
        SetRateAltitudeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAltitudeRequest, _mavsdk_rpc_telemetry_SetRateAltitudeRequest__Output>
        SetRateAltitudeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAltitudeResponse, _mavsdk_rpc_telemetry_SetRateAltitudeResponse__Output>
        SetRateAttitudeAngularVelocityBodyRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyRequest, _mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyRequest__Output>
        SetRateAttitudeAngularVelocityBodyResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyResponse, _mavsdk_rpc_telemetry_SetRateAttitudeAngularVelocityBodyResponse__Output>
        SetRateAttitudeEulerRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest, _mavsdk_rpc_telemetry_SetRateAttitudeEulerRequest__Output>
        SetRateAttitudeEulerResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse, _mavsdk_rpc_telemetry_SetRateAttitudeEulerResponse__Output>
        SetRateAttitudeQuaternionRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest, _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionRequest__Output>
        SetRateAttitudeQuaternionResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse, _mavsdk_rpc_telemetry_SetRateAttitudeQuaternionResponse__Output>
        SetRateBatteryRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateBatteryRequest, _mavsdk_rpc_telemetry_SetRateBatteryRequest__Output>
        SetRateBatteryResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateBatteryResponse, _mavsdk_rpc_telemetry_SetRateBatteryResponse__Output>
        SetRateDistanceSensorRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateDistanceSensorRequest, _mavsdk_rpc_telemetry_SetRateDistanceSensorRequest__Output>
        SetRateDistanceSensorResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateDistanceSensorResponse, _mavsdk_rpc_telemetry_SetRateDistanceSensorResponse__Output>
        SetRateFixedwingMetricsRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest, _mavsdk_rpc_telemetry_SetRateFixedwingMetricsRequest__Output>
        SetRateFixedwingMetricsResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse, _mavsdk_rpc_telemetry_SetRateFixedwingMetricsResponse__Output>
        SetRateGpsInfoRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateGpsInfoRequest, _mavsdk_rpc_telemetry_SetRateGpsInfoRequest__Output>
        SetRateGpsInfoResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateGpsInfoResponse, _mavsdk_rpc_telemetry_SetRateGpsInfoResponse__Output>
        SetRateGroundTruthRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateGroundTruthRequest, _mavsdk_rpc_telemetry_SetRateGroundTruthRequest__Output>
        SetRateGroundTruthResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateGroundTruthResponse, _mavsdk_rpc_telemetry_SetRateGroundTruthResponse__Output>
        SetRateHealthRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateHealthRequest, _mavsdk_rpc_telemetry_SetRateHealthRequest__Output>
        SetRateHealthResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateHealthResponse, _mavsdk_rpc_telemetry_SetRateHealthResponse__Output>
        SetRateHomeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateHomeRequest, _mavsdk_rpc_telemetry_SetRateHomeRequest__Output>
        SetRateHomeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateHomeResponse, _mavsdk_rpc_telemetry_SetRateHomeResponse__Output>
        SetRateImuRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateImuRequest, _mavsdk_rpc_telemetry_SetRateImuRequest__Output>
        SetRateImuResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateImuResponse, _mavsdk_rpc_telemetry_SetRateImuResponse__Output>
        SetRateInAirRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateInAirRequest, _mavsdk_rpc_telemetry_SetRateInAirRequest__Output>
        SetRateInAirResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateInAirResponse, _mavsdk_rpc_telemetry_SetRateInAirResponse__Output>
        SetRateLandedStateRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateLandedStateRequest, _mavsdk_rpc_telemetry_SetRateLandedStateRequest__Output>
        SetRateLandedStateResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateLandedStateResponse, _mavsdk_rpc_telemetry_SetRateLandedStateResponse__Output>
        SetRateOdometryRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateOdometryRequest, _mavsdk_rpc_telemetry_SetRateOdometryRequest__Output>
        SetRateOdometryResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateOdometryResponse, _mavsdk_rpc_telemetry_SetRateOdometryResponse__Output>
        SetRatePositionRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRatePositionRequest, _mavsdk_rpc_telemetry_SetRatePositionRequest__Output>
        SetRatePositionResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRatePositionResponse, _mavsdk_rpc_telemetry_SetRatePositionResponse__Output>
        SetRatePositionVelocityNedRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest, _mavsdk_rpc_telemetry_SetRatePositionVelocityNedRequest__Output>
        SetRatePositionVelocityNedResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse, _mavsdk_rpc_telemetry_SetRatePositionVelocityNedResponse__Output>
        SetRateRawGpsRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateRawGpsRequest, _mavsdk_rpc_telemetry_SetRateRawGpsRequest__Output>
        SetRateRawGpsResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateRawGpsResponse, _mavsdk_rpc_telemetry_SetRateRawGpsResponse__Output>
        SetRateRawImuRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateRawImuRequest, _mavsdk_rpc_telemetry_SetRateRawImuRequest__Output>
        SetRateRawImuResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateRawImuResponse, _mavsdk_rpc_telemetry_SetRateRawImuResponse__Output>
        SetRateRcStatusRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateRcStatusRequest, _mavsdk_rpc_telemetry_SetRateRcStatusRequest__Output>
        SetRateRcStatusResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateRcStatusResponse, _mavsdk_rpc_telemetry_SetRateRcStatusResponse__Output>
        SetRateScaledImuRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateScaledImuRequest, _mavsdk_rpc_telemetry_SetRateScaledImuRequest__Output>
        SetRateScaledImuResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateScaledImuResponse, _mavsdk_rpc_telemetry_SetRateScaledImuResponse__Output>
        SetRateUnixEpochTimeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest, _mavsdk_rpc_telemetry_SetRateUnixEpochTimeRequest__Output>
        SetRateUnixEpochTimeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse, _mavsdk_rpc_telemetry_SetRateUnixEpochTimeResponse__Output>
        SetRateVelocityNedRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateVelocityNedRequest, _mavsdk_rpc_telemetry_SetRateVelocityNedRequest__Output>
        SetRateVelocityNedResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateVelocityNedResponse, _mavsdk_rpc_telemetry_SetRateVelocityNedResponse__Output>
        SetRateVtolStateRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateVtolStateRequest, _mavsdk_rpc_telemetry_SetRateVtolStateRequest__Output>
        SetRateVtolStateResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_SetRateVtolStateResponse, _mavsdk_rpc_telemetry_SetRateVtolStateResponse__Output>
        StatusText: MessageTypeDefinition<_mavsdk_rpc_telemetry_StatusText, _mavsdk_rpc_telemetry_StatusText__Output>
        StatusTextResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_StatusTextResponse, _mavsdk_rpc_telemetry_StatusTextResponse__Output>
        StatusTextType: EnumTypeDefinition
        SubscribeActuatorControlTargetRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest, _mavsdk_rpc_telemetry_SubscribeActuatorControlTargetRequest__Output>
        SubscribeActuatorOutputStatusRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest, _mavsdk_rpc_telemetry_SubscribeActuatorOutputStatusRequest__Output>
        SubscribeAltitudeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeAltitudeRequest, _mavsdk_rpc_telemetry_SubscribeAltitudeRequest__Output>
        SubscribeArmedRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeArmedRequest, _mavsdk_rpc_telemetry_SubscribeArmedRequest__Output>
        SubscribeAttitudeAngularVelocityBodyRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest, _mavsdk_rpc_telemetry_SubscribeAttitudeAngularVelocityBodyRequest__Output>
        SubscribeAttitudeEulerRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest, _mavsdk_rpc_telemetry_SubscribeAttitudeEulerRequest__Output>
        SubscribeAttitudeQuaternionRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest, _mavsdk_rpc_telemetry_SubscribeAttitudeQuaternionRequest__Output>
        SubscribeBatteryRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeBatteryRequest, _mavsdk_rpc_telemetry_SubscribeBatteryRequest__Output>
        SubscribeDistanceSensorRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest, _mavsdk_rpc_telemetry_SubscribeDistanceSensorRequest__Output>
        SubscribeFixedwingMetricsRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest, _mavsdk_rpc_telemetry_SubscribeFixedwingMetricsRequest__Output>
        SubscribeFlightModeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeFlightModeRequest, _mavsdk_rpc_telemetry_SubscribeFlightModeRequest__Output>
        SubscribeGpsInfoRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeGpsInfoRequest, _mavsdk_rpc_telemetry_SubscribeGpsInfoRequest__Output>
        SubscribeGroundTruthRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeGroundTruthRequest, _mavsdk_rpc_telemetry_SubscribeGroundTruthRequest__Output>
        SubscribeHeadingRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeHeadingRequest, _mavsdk_rpc_telemetry_SubscribeHeadingRequest__Output>
        SubscribeHealthAllOkRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest, _mavsdk_rpc_telemetry_SubscribeHealthAllOkRequest__Output>
        SubscribeHealthRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeHealthRequest, _mavsdk_rpc_telemetry_SubscribeHealthRequest__Output>
        SubscribeHomeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeHomeRequest, _mavsdk_rpc_telemetry_SubscribeHomeRequest__Output>
        SubscribeImuRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeImuRequest, _mavsdk_rpc_telemetry_SubscribeImuRequest__Output>
        SubscribeInAirRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeInAirRequest, _mavsdk_rpc_telemetry_SubscribeInAirRequest__Output>
        SubscribeLandedStateRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeLandedStateRequest, _mavsdk_rpc_telemetry_SubscribeLandedStateRequest__Output>
        SubscribeOdometryRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeOdometryRequest, _mavsdk_rpc_telemetry_SubscribeOdometryRequest__Output>
        SubscribePositionRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribePositionRequest, _mavsdk_rpc_telemetry_SubscribePositionRequest__Output>
        SubscribePositionVelocityNedRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest, _mavsdk_rpc_telemetry_SubscribePositionVelocityNedRequest__Output>
        SubscribeRawGpsRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeRawGpsRequest, _mavsdk_rpc_telemetry_SubscribeRawGpsRequest__Output>
        SubscribeRawImuRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeRawImuRequest, _mavsdk_rpc_telemetry_SubscribeRawImuRequest__Output>
        SubscribeRcStatusRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeRcStatusRequest, _mavsdk_rpc_telemetry_SubscribeRcStatusRequest__Output>
        SubscribeScaledImuRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeScaledImuRequest, _mavsdk_rpc_telemetry_SubscribeScaledImuRequest__Output>
        SubscribeScaledPressureRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeScaledPressureRequest, _mavsdk_rpc_telemetry_SubscribeScaledPressureRequest__Output>
        SubscribeStatusTextRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeStatusTextRequest, _mavsdk_rpc_telemetry_SubscribeStatusTextRequest__Output>
        SubscribeUnixEpochTimeRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest, _mavsdk_rpc_telemetry_SubscribeUnixEpochTimeRequest__Output>
        SubscribeVelocityNedRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeVelocityNedRequest, _mavsdk_rpc_telemetry_SubscribeVelocityNedRequest__Output>
        SubscribeVtolStateRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeVtolStateRequest, _mavsdk_rpc_telemetry_SubscribeVtolStateRequest__Output>
        SubscribeWindRequest: MessageTypeDefinition<_mavsdk_rpc_telemetry_SubscribeWindRequest, _mavsdk_rpc_telemetry_SubscribeWindRequest__Output>
        TelemetryResult: MessageTypeDefinition<_mavsdk_rpc_telemetry_TelemetryResult, _mavsdk_rpc_telemetry_TelemetryResult__Output>
        TelemetryService: SubtypeConstructor<typeof grpc.Client, _mavsdk_rpc_telemetry_TelemetryServiceClient> & { service: _mavsdk_rpc_telemetry_TelemetryServiceDefinition }
        UnixEpochTimeResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_UnixEpochTimeResponse, _mavsdk_rpc_telemetry_UnixEpochTimeResponse__Output>
        VelocityBody: MessageTypeDefinition<_mavsdk_rpc_telemetry_VelocityBody, _mavsdk_rpc_telemetry_VelocityBody__Output>
        VelocityNed: MessageTypeDefinition<_mavsdk_rpc_telemetry_VelocityNed, _mavsdk_rpc_telemetry_VelocityNed__Output>
        VelocityNedResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_VelocityNedResponse, _mavsdk_rpc_telemetry_VelocityNedResponse__Output>
        VtolState: EnumTypeDefinition
        VtolStateResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_VtolStateResponse, _mavsdk_rpc_telemetry_VtolStateResponse__Output>
        Wind: MessageTypeDefinition<_mavsdk_rpc_telemetry_Wind, _mavsdk_rpc_telemetry_Wind__Output>
        WindResponse: MessageTypeDefinition<_mavsdk_rpc_telemetry_WindResponse, _mavsdk_rpc_telemetry_WindResponse__Output>
      }
    }
  }
}

