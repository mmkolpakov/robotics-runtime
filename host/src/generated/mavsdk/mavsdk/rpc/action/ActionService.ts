// Original file: proto/action/action.proto

import type * as grpc from '@grpc/grpc-js'
import type { MethodDefinition } from '@grpc/proto-loader'
import type { ArmForceRequest as _mavsdk_rpc_action_ArmForceRequest, ArmForceRequest__Output as _mavsdk_rpc_action_ArmForceRequest__Output } from '../../../mavsdk/rpc/action/ArmForceRequest.js';
import type { ArmForceResponse as _mavsdk_rpc_action_ArmForceResponse, ArmForceResponse__Output as _mavsdk_rpc_action_ArmForceResponse__Output } from '../../../mavsdk/rpc/action/ArmForceResponse.js';
import type { ArmRequest as _mavsdk_rpc_action_ArmRequest, ArmRequest__Output as _mavsdk_rpc_action_ArmRequest__Output } from '../../../mavsdk/rpc/action/ArmRequest.js';
import type { ArmResponse as _mavsdk_rpc_action_ArmResponse, ArmResponse__Output as _mavsdk_rpc_action_ArmResponse__Output } from '../../../mavsdk/rpc/action/ArmResponse.js';
import type { DisarmRequest as _mavsdk_rpc_action_DisarmRequest, DisarmRequest__Output as _mavsdk_rpc_action_DisarmRequest__Output } from '../../../mavsdk/rpc/action/DisarmRequest.js';
import type { DisarmResponse as _mavsdk_rpc_action_DisarmResponse, DisarmResponse__Output as _mavsdk_rpc_action_DisarmResponse__Output } from '../../../mavsdk/rpc/action/DisarmResponse.js';
import type { DoOrbitRequest as _mavsdk_rpc_action_DoOrbitRequest, DoOrbitRequest__Output as _mavsdk_rpc_action_DoOrbitRequest__Output } from '../../../mavsdk/rpc/action/DoOrbitRequest.js';
import type { DoOrbitResponse as _mavsdk_rpc_action_DoOrbitResponse, DoOrbitResponse__Output as _mavsdk_rpc_action_DoOrbitResponse__Output } from '../../../mavsdk/rpc/action/DoOrbitResponse.js';
import type { GetReturnToLaunchAltitudeRequest as _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, GetReturnToLaunchAltitudeRequest__Output as _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest__Output } from '../../../mavsdk/rpc/action/GetReturnToLaunchAltitudeRequest.js';
import type { GetReturnToLaunchAltitudeResponse as _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse, GetReturnToLaunchAltitudeResponse__Output as _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output } from '../../../mavsdk/rpc/action/GetReturnToLaunchAltitudeResponse.js';
import type { GetTakeoffAltitudeRequest as _mavsdk_rpc_action_GetTakeoffAltitudeRequest, GetTakeoffAltitudeRequest__Output as _mavsdk_rpc_action_GetTakeoffAltitudeRequest__Output } from '../../../mavsdk/rpc/action/GetTakeoffAltitudeRequest.js';
import type { GetTakeoffAltitudeResponse as _mavsdk_rpc_action_GetTakeoffAltitudeResponse, GetTakeoffAltitudeResponse__Output as _mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output } from '../../../mavsdk/rpc/action/GetTakeoffAltitudeResponse.js';
import type { GotoLocationFixedwingRequest as _mavsdk_rpc_action_GotoLocationFixedwingRequest, GotoLocationFixedwingRequest__Output as _mavsdk_rpc_action_GotoLocationFixedwingRequest__Output } from '../../../mavsdk/rpc/action/GotoLocationFixedwingRequest.js';
import type { GotoLocationFixedwingResponse as _mavsdk_rpc_action_GotoLocationFixedwingResponse, GotoLocationFixedwingResponse__Output as _mavsdk_rpc_action_GotoLocationFixedwingResponse__Output } from '../../../mavsdk/rpc/action/GotoLocationFixedwingResponse.js';
import type { GotoLocationRequest as _mavsdk_rpc_action_GotoLocationRequest, GotoLocationRequest__Output as _mavsdk_rpc_action_GotoLocationRequest__Output } from '../../../mavsdk/rpc/action/GotoLocationRequest.js';
import type { GotoLocationResponse as _mavsdk_rpc_action_GotoLocationResponse, GotoLocationResponse__Output as _mavsdk_rpc_action_GotoLocationResponse__Output } from '../../../mavsdk/rpc/action/GotoLocationResponse.js';
import type { HoldRequest as _mavsdk_rpc_action_HoldRequest, HoldRequest__Output as _mavsdk_rpc_action_HoldRequest__Output } from '../../../mavsdk/rpc/action/HoldRequest.js';
import type { HoldResponse as _mavsdk_rpc_action_HoldResponse, HoldResponse__Output as _mavsdk_rpc_action_HoldResponse__Output } from '../../../mavsdk/rpc/action/HoldResponse.js';
import type { KillRequest as _mavsdk_rpc_action_KillRequest, KillRequest__Output as _mavsdk_rpc_action_KillRequest__Output } from '../../../mavsdk/rpc/action/KillRequest.js';
import type { KillResponse as _mavsdk_rpc_action_KillResponse, KillResponse__Output as _mavsdk_rpc_action_KillResponse__Output } from '../../../mavsdk/rpc/action/KillResponse.js';
import type { LandRequest as _mavsdk_rpc_action_LandRequest, LandRequest__Output as _mavsdk_rpc_action_LandRequest__Output } from '../../../mavsdk/rpc/action/LandRequest.js';
import type { LandResponse as _mavsdk_rpc_action_LandResponse, LandResponse__Output as _mavsdk_rpc_action_LandResponse__Output } from '../../../mavsdk/rpc/action/LandResponse.js';
import type { RebootRequest as _mavsdk_rpc_action_RebootRequest, RebootRequest__Output as _mavsdk_rpc_action_RebootRequest__Output } from '../../../mavsdk/rpc/action/RebootRequest.js';
import type { RebootResponse as _mavsdk_rpc_action_RebootResponse, RebootResponse__Output as _mavsdk_rpc_action_RebootResponse__Output } from '../../../mavsdk/rpc/action/RebootResponse.js';
import type { ReturnToLaunchRequest as _mavsdk_rpc_action_ReturnToLaunchRequest, ReturnToLaunchRequest__Output as _mavsdk_rpc_action_ReturnToLaunchRequest__Output } from '../../../mavsdk/rpc/action/ReturnToLaunchRequest.js';
import type { ReturnToLaunchResponse as _mavsdk_rpc_action_ReturnToLaunchResponse, ReturnToLaunchResponse__Output as _mavsdk_rpc_action_ReturnToLaunchResponse__Output } from '../../../mavsdk/rpc/action/ReturnToLaunchResponse.js';
import type { SetActuatorRequest as _mavsdk_rpc_action_SetActuatorRequest, SetActuatorRequest__Output as _mavsdk_rpc_action_SetActuatorRequest__Output } from '../../../mavsdk/rpc/action/SetActuatorRequest.js';
import type { SetActuatorResponse as _mavsdk_rpc_action_SetActuatorResponse, SetActuatorResponse__Output as _mavsdk_rpc_action_SetActuatorResponse__Output } from '../../../mavsdk/rpc/action/SetActuatorResponse.js';
import type { SetCurrentSpeedRequest as _mavsdk_rpc_action_SetCurrentSpeedRequest, SetCurrentSpeedRequest__Output as _mavsdk_rpc_action_SetCurrentSpeedRequest__Output } from '../../../mavsdk/rpc/action/SetCurrentSpeedRequest.js';
import type { SetCurrentSpeedResponse as _mavsdk_rpc_action_SetCurrentSpeedResponse, SetCurrentSpeedResponse__Output as _mavsdk_rpc_action_SetCurrentSpeedResponse__Output } from '../../../mavsdk/rpc/action/SetCurrentSpeedResponse.js';
import type { SetGpsGlobalOriginRequest as _mavsdk_rpc_action_SetGpsGlobalOriginRequest, SetGpsGlobalOriginRequest__Output as _mavsdk_rpc_action_SetGpsGlobalOriginRequest__Output } from '../../../mavsdk/rpc/action/SetGpsGlobalOriginRequest.js';
import type { SetGpsGlobalOriginResponse as _mavsdk_rpc_action_SetGpsGlobalOriginResponse, SetGpsGlobalOriginResponse__Output as _mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output } from '../../../mavsdk/rpc/action/SetGpsGlobalOriginResponse.js';
import type { SetHomeRequest as _mavsdk_rpc_action_SetHomeRequest, SetHomeRequest__Output as _mavsdk_rpc_action_SetHomeRequest__Output } from '../../../mavsdk/rpc/action/SetHomeRequest.js';
import type { SetHomeResponse as _mavsdk_rpc_action_SetHomeResponse, SetHomeResponse__Output as _mavsdk_rpc_action_SetHomeResponse__Output } from '../../../mavsdk/rpc/action/SetHomeResponse.js';
import type { SetRelayRequest as _mavsdk_rpc_action_SetRelayRequest, SetRelayRequest__Output as _mavsdk_rpc_action_SetRelayRequest__Output } from '../../../mavsdk/rpc/action/SetRelayRequest.js';
import type { SetRelayResponse as _mavsdk_rpc_action_SetRelayResponse, SetRelayResponse__Output as _mavsdk_rpc_action_SetRelayResponse__Output } from '../../../mavsdk/rpc/action/SetRelayResponse.js';
import type { SetReturnToLaunchAltitudeRequest as _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, SetReturnToLaunchAltitudeRequest__Output as _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest__Output } from '../../../mavsdk/rpc/action/SetReturnToLaunchAltitudeRequest.js';
import type { SetReturnToLaunchAltitudeResponse as _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse, SetReturnToLaunchAltitudeResponse__Output as _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output } from '../../../mavsdk/rpc/action/SetReturnToLaunchAltitudeResponse.js';
import type { SetTakeoffAltitudeRequest as _mavsdk_rpc_action_SetTakeoffAltitudeRequest, SetTakeoffAltitudeRequest__Output as _mavsdk_rpc_action_SetTakeoffAltitudeRequest__Output } from '../../../mavsdk/rpc/action/SetTakeoffAltitudeRequest.js';
import type { SetTakeoffAltitudeResponse as _mavsdk_rpc_action_SetTakeoffAltitudeResponse, SetTakeoffAltitudeResponse__Output as _mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output } from '../../../mavsdk/rpc/action/SetTakeoffAltitudeResponse.js';
import type { ShutdownRequest as _mavsdk_rpc_action_ShutdownRequest, ShutdownRequest__Output as _mavsdk_rpc_action_ShutdownRequest__Output } from '../../../mavsdk/rpc/action/ShutdownRequest.js';
import type { ShutdownResponse as _mavsdk_rpc_action_ShutdownResponse, ShutdownResponse__Output as _mavsdk_rpc_action_ShutdownResponse__Output } from '../../../mavsdk/rpc/action/ShutdownResponse.js';
import type { TakeoffRequest as _mavsdk_rpc_action_TakeoffRequest, TakeoffRequest__Output as _mavsdk_rpc_action_TakeoffRequest__Output } from '../../../mavsdk/rpc/action/TakeoffRequest.js';
import type { TakeoffResponse as _mavsdk_rpc_action_TakeoffResponse, TakeoffResponse__Output as _mavsdk_rpc_action_TakeoffResponse__Output } from '../../../mavsdk/rpc/action/TakeoffResponse.js';
import type { TerminateRequest as _mavsdk_rpc_action_TerminateRequest, TerminateRequest__Output as _mavsdk_rpc_action_TerminateRequest__Output } from '../../../mavsdk/rpc/action/TerminateRequest.js';
import type { TerminateResponse as _mavsdk_rpc_action_TerminateResponse, TerminateResponse__Output as _mavsdk_rpc_action_TerminateResponse__Output } from '../../../mavsdk/rpc/action/TerminateResponse.js';
import type { TransitionToFixedwingRequest as _mavsdk_rpc_action_TransitionToFixedwingRequest, TransitionToFixedwingRequest__Output as _mavsdk_rpc_action_TransitionToFixedwingRequest__Output } from '../../../mavsdk/rpc/action/TransitionToFixedwingRequest.js';
import type { TransitionToFixedwingResponse as _mavsdk_rpc_action_TransitionToFixedwingResponse, TransitionToFixedwingResponse__Output as _mavsdk_rpc_action_TransitionToFixedwingResponse__Output } from '../../../mavsdk/rpc/action/TransitionToFixedwingResponse.js';
import type { TransitionToMulticopterRequest as _mavsdk_rpc_action_TransitionToMulticopterRequest, TransitionToMulticopterRequest__Output as _mavsdk_rpc_action_TransitionToMulticopterRequest__Output } from '../../../mavsdk/rpc/action/TransitionToMulticopterRequest.js';
import type { TransitionToMulticopterResponse as _mavsdk_rpc_action_TransitionToMulticopterResponse, TransitionToMulticopterResponse__Output as _mavsdk_rpc_action_TransitionToMulticopterResponse__Output } from '../../../mavsdk/rpc/action/TransitionToMulticopterResponse.js';

export interface ActionServiceClient extends grpc.Client {
  Arm(argument: _mavsdk_rpc_action_ArmRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  Arm(argument: _mavsdk_rpc_action_ArmRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  Arm(argument: _mavsdk_rpc_action_ArmRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  Arm(argument: _mavsdk_rpc_action_ArmRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  arm(argument: _mavsdk_rpc_action_ArmRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  arm(argument: _mavsdk_rpc_action_ArmRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  arm(argument: _mavsdk_rpc_action_ArmRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  arm(argument: _mavsdk_rpc_action_ArmRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmResponse__Output>): grpc.ClientUnaryCall;
  
  ArmForce(argument: _mavsdk_rpc_action_ArmForceRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  ArmForce(argument: _mavsdk_rpc_action_ArmForceRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  ArmForce(argument: _mavsdk_rpc_action_ArmForceRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  ArmForce(argument: _mavsdk_rpc_action_ArmForceRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  armForce(argument: _mavsdk_rpc_action_ArmForceRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  armForce(argument: _mavsdk_rpc_action_ArmForceRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  armForce(argument: _mavsdk_rpc_action_ArmForceRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  armForce(argument: _mavsdk_rpc_action_ArmForceRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ArmForceResponse__Output>): grpc.ClientUnaryCall;
  
  Disarm(argument: _mavsdk_rpc_action_DisarmRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  Disarm(argument: _mavsdk_rpc_action_DisarmRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  Disarm(argument: _mavsdk_rpc_action_DisarmRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  Disarm(argument: _mavsdk_rpc_action_DisarmRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  disarm(argument: _mavsdk_rpc_action_DisarmRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  disarm(argument: _mavsdk_rpc_action_DisarmRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  disarm(argument: _mavsdk_rpc_action_DisarmRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  disarm(argument: _mavsdk_rpc_action_DisarmRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_DisarmResponse__Output>): grpc.ClientUnaryCall;
  
  DoOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  DoOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  DoOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  DoOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  doOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  doOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  doOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  doOrbit(argument: _mavsdk_rpc_action_DoOrbitRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_DoOrbitResponse__Output>): grpc.ClientUnaryCall;
  
  GetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  GetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  GetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  GetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getReturnToLaunchAltitude(argument: _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  
  GetTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  GetTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  GetTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  GetTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  getTakeoffAltitude(argument: _mavsdk_rpc_action_GetTakeoffAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  
  GotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  GotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  GotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  GotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  gotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  gotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  gotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  gotoLocation(argument: _mavsdk_rpc_action_GotoLocationRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationResponse__Output>): grpc.ClientUnaryCall;
  
  GotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  GotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  GotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  GotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  gotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  gotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  gotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  gotoLocationFixedwing(argument: _mavsdk_rpc_action_GotoLocationFixedwingRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>): grpc.ClientUnaryCall;
  
  Hold(argument: _mavsdk_rpc_action_HoldRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  Hold(argument: _mavsdk_rpc_action_HoldRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  Hold(argument: _mavsdk_rpc_action_HoldRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  Hold(argument: _mavsdk_rpc_action_HoldRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  hold(argument: _mavsdk_rpc_action_HoldRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  hold(argument: _mavsdk_rpc_action_HoldRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  hold(argument: _mavsdk_rpc_action_HoldRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  hold(argument: _mavsdk_rpc_action_HoldRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_HoldResponse__Output>): grpc.ClientUnaryCall;
  
  Kill(argument: _mavsdk_rpc_action_KillRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  Kill(argument: _mavsdk_rpc_action_KillRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  Kill(argument: _mavsdk_rpc_action_KillRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  Kill(argument: _mavsdk_rpc_action_KillRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  kill(argument: _mavsdk_rpc_action_KillRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  kill(argument: _mavsdk_rpc_action_KillRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  kill(argument: _mavsdk_rpc_action_KillRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  kill(argument: _mavsdk_rpc_action_KillRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_KillResponse__Output>): grpc.ClientUnaryCall;
  
  Land(argument: _mavsdk_rpc_action_LandRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  Land(argument: _mavsdk_rpc_action_LandRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  Land(argument: _mavsdk_rpc_action_LandRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  Land(argument: _mavsdk_rpc_action_LandRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  land(argument: _mavsdk_rpc_action_LandRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  land(argument: _mavsdk_rpc_action_LandRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  land(argument: _mavsdk_rpc_action_LandRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  land(argument: _mavsdk_rpc_action_LandRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_LandResponse__Output>): grpc.ClientUnaryCall;
  
  Reboot(argument: _mavsdk_rpc_action_RebootRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  Reboot(argument: _mavsdk_rpc_action_RebootRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  Reboot(argument: _mavsdk_rpc_action_RebootRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  Reboot(argument: _mavsdk_rpc_action_RebootRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  reboot(argument: _mavsdk_rpc_action_RebootRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  reboot(argument: _mavsdk_rpc_action_RebootRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  reboot(argument: _mavsdk_rpc_action_RebootRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  reboot(argument: _mavsdk_rpc_action_RebootRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_RebootResponse__Output>): grpc.ClientUnaryCall;
  
  ReturnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  ReturnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  ReturnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  ReturnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  returnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  returnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  returnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  returnToLaunch(argument: _mavsdk_rpc_action_ReturnToLaunchRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ReturnToLaunchResponse__Output>): grpc.ClientUnaryCall;
  
  SetActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  SetActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  SetActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  SetActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  setActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  setActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  setActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  setActuator(argument: _mavsdk_rpc_action_SetActuatorRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetActuatorResponse__Output>): grpc.ClientUnaryCall;
  
  SetCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  SetCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  SetCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  SetCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  setCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  setCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  setCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  setCurrentSpeed(argument: _mavsdk_rpc_action_SetCurrentSpeedRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetCurrentSpeedResponse__Output>): grpc.ClientUnaryCall;
  
  SetGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  SetGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  SetGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  SetGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  setGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  setGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  setGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  setGpsGlobalOrigin(argument: _mavsdk_rpc_action_SetGpsGlobalOriginRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>): grpc.ClientUnaryCall;
  
  SetHome(argument: _mavsdk_rpc_action_SetHomeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  SetHome(argument: _mavsdk_rpc_action_SetHomeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  SetHome(argument: _mavsdk_rpc_action_SetHomeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  SetHome(argument: _mavsdk_rpc_action_SetHomeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  setHome(argument: _mavsdk_rpc_action_SetHomeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  setHome(argument: _mavsdk_rpc_action_SetHomeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  setHome(argument: _mavsdk_rpc_action_SetHomeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  setHome(argument: _mavsdk_rpc_action_SetHomeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetHomeResponse__Output>): grpc.ClientUnaryCall;
  
  SetRelay(argument: _mavsdk_rpc_action_SetRelayRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  SetRelay(argument: _mavsdk_rpc_action_SetRelayRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  SetRelay(argument: _mavsdk_rpc_action_SetRelayRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  SetRelay(argument: _mavsdk_rpc_action_SetRelayRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  setRelay(argument: _mavsdk_rpc_action_SetRelayRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  setRelay(argument: _mavsdk_rpc_action_SetRelayRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  setRelay(argument: _mavsdk_rpc_action_SetRelayRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  setRelay(argument: _mavsdk_rpc_action_SetRelayRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetRelayResponse__Output>): grpc.ClientUnaryCall;
  
  SetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setReturnToLaunchAltitude(argument: _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>): grpc.ClientUnaryCall;
  
  SetTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  SetTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  setTakeoffAltitude(argument: _mavsdk_rpc_action_SetTakeoffAltitudeRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>): grpc.ClientUnaryCall;
  
  Shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  Shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  Shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  Shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  shutdown(argument: _mavsdk_rpc_action_ShutdownRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_ShutdownResponse__Output>): grpc.ClientUnaryCall;
  
  Takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  Takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  Takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  Takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  takeoff(argument: _mavsdk_rpc_action_TakeoffRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TakeoffResponse__Output>): grpc.ClientUnaryCall;
  
  Terminate(argument: _mavsdk_rpc_action_TerminateRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  Terminate(argument: _mavsdk_rpc_action_TerminateRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  Terminate(argument: _mavsdk_rpc_action_TerminateRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  Terminate(argument: _mavsdk_rpc_action_TerminateRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  terminate(argument: _mavsdk_rpc_action_TerminateRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  terminate(argument: _mavsdk_rpc_action_TerminateRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  terminate(argument: _mavsdk_rpc_action_TerminateRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  terminate(argument: _mavsdk_rpc_action_TerminateRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TerminateResponse__Output>): grpc.ClientUnaryCall;
  
  TransitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  TransitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  TransitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  TransitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  transitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  transitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  transitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  transitionToFixedwing(argument: _mavsdk_rpc_action_TransitionToFixedwingRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToFixedwingResponse__Output>): grpc.ClientUnaryCall;
  
  TransitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  TransitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  TransitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  TransitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  transitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, metadata: grpc.Metadata, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  transitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, metadata: grpc.Metadata, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  transitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, options: grpc.CallOptions, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  transitionToMulticopter(argument: _mavsdk_rpc_action_TransitionToMulticopterRequest, callback: grpc.requestCallback<_mavsdk_rpc_action_TransitionToMulticopterResponse__Output>): grpc.ClientUnaryCall;
  
}

export interface ActionServiceHandlers extends grpc.UntypedServiceImplementation {
  Arm: grpc.handleUnaryCall<_mavsdk_rpc_action_ArmRequest__Output, _mavsdk_rpc_action_ArmResponse>;
  
  ArmForce: grpc.handleUnaryCall<_mavsdk_rpc_action_ArmForceRequest__Output, _mavsdk_rpc_action_ArmForceResponse>;
  
  Disarm: grpc.handleUnaryCall<_mavsdk_rpc_action_DisarmRequest__Output, _mavsdk_rpc_action_DisarmResponse>;
  
  DoOrbit: grpc.handleUnaryCall<_mavsdk_rpc_action_DoOrbitRequest__Output, _mavsdk_rpc_action_DoOrbitResponse>;
  
  GetReturnToLaunchAltitude: grpc.handleUnaryCall<_mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest__Output, _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse>;
  
  GetTakeoffAltitude: grpc.handleUnaryCall<_mavsdk_rpc_action_GetTakeoffAltitudeRequest__Output, _mavsdk_rpc_action_GetTakeoffAltitudeResponse>;
  
  GotoLocation: grpc.handleUnaryCall<_mavsdk_rpc_action_GotoLocationRequest__Output, _mavsdk_rpc_action_GotoLocationResponse>;
  
  GotoLocationFixedwing: grpc.handleUnaryCall<_mavsdk_rpc_action_GotoLocationFixedwingRequest__Output, _mavsdk_rpc_action_GotoLocationFixedwingResponse>;
  
  Hold: grpc.handleUnaryCall<_mavsdk_rpc_action_HoldRequest__Output, _mavsdk_rpc_action_HoldResponse>;
  
  Kill: grpc.handleUnaryCall<_mavsdk_rpc_action_KillRequest__Output, _mavsdk_rpc_action_KillResponse>;
  
  Land: grpc.handleUnaryCall<_mavsdk_rpc_action_LandRequest__Output, _mavsdk_rpc_action_LandResponse>;
  
  Reboot: grpc.handleUnaryCall<_mavsdk_rpc_action_RebootRequest__Output, _mavsdk_rpc_action_RebootResponse>;
  
  ReturnToLaunch: grpc.handleUnaryCall<_mavsdk_rpc_action_ReturnToLaunchRequest__Output, _mavsdk_rpc_action_ReturnToLaunchResponse>;
  
  SetActuator: grpc.handleUnaryCall<_mavsdk_rpc_action_SetActuatorRequest__Output, _mavsdk_rpc_action_SetActuatorResponse>;
  
  SetCurrentSpeed: grpc.handleUnaryCall<_mavsdk_rpc_action_SetCurrentSpeedRequest__Output, _mavsdk_rpc_action_SetCurrentSpeedResponse>;
  
  SetGpsGlobalOrigin: grpc.handleUnaryCall<_mavsdk_rpc_action_SetGpsGlobalOriginRequest__Output, _mavsdk_rpc_action_SetGpsGlobalOriginResponse>;
  
  SetHome: grpc.handleUnaryCall<_mavsdk_rpc_action_SetHomeRequest__Output, _mavsdk_rpc_action_SetHomeResponse>;
  
  SetRelay: grpc.handleUnaryCall<_mavsdk_rpc_action_SetRelayRequest__Output, _mavsdk_rpc_action_SetRelayResponse>;
  
  SetReturnToLaunchAltitude: grpc.handleUnaryCall<_mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest__Output, _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse>;
  
  SetTakeoffAltitude: grpc.handleUnaryCall<_mavsdk_rpc_action_SetTakeoffAltitudeRequest__Output, _mavsdk_rpc_action_SetTakeoffAltitudeResponse>;
  
  Shutdown: grpc.handleUnaryCall<_mavsdk_rpc_action_ShutdownRequest__Output, _mavsdk_rpc_action_ShutdownResponse>;
  
  Takeoff: grpc.handleUnaryCall<_mavsdk_rpc_action_TakeoffRequest__Output, _mavsdk_rpc_action_TakeoffResponse>;
  
  Terminate: grpc.handleUnaryCall<_mavsdk_rpc_action_TerminateRequest__Output, _mavsdk_rpc_action_TerminateResponse>;
  
  TransitionToFixedwing: grpc.handleUnaryCall<_mavsdk_rpc_action_TransitionToFixedwingRequest__Output, _mavsdk_rpc_action_TransitionToFixedwingResponse>;
  
  TransitionToMulticopter: grpc.handleUnaryCall<_mavsdk_rpc_action_TransitionToMulticopterRequest__Output, _mavsdk_rpc_action_TransitionToMulticopterResponse>;
  
}

export interface ActionServiceDefinition extends grpc.ServiceDefinition {
  Arm: MethodDefinition<_mavsdk_rpc_action_ArmRequest, _mavsdk_rpc_action_ArmResponse, _mavsdk_rpc_action_ArmRequest__Output, _mavsdk_rpc_action_ArmResponse__Output>
  ArmForce: MethodDefinition<_mavsdk_rpc_action_ArmForceRequest, _mavsdk_rpc_action_ArmForceResponse, _mavsdk_rpc_action_ArmForceRequest__Output, _mavsdk_rpc_action_ArmForceResponse__Output>
  Disarm: MethodDefinition<_mavsdk_rpc_action_DisarmRequest, _mavsdk_rpc_action_DisarmResponse, _mavsdk_rpc_action_DisarmRequest__Output, _mavsdk_rpc_action_DisarmResponse__Output>
  DoOrbit: MethodDefinition<_mavsdk_rpc_action_DoOrbitRequest, _mavsdk_rpc_action_DoOrbitResponse, _mavsdk_rpc_action_DoOrbitRequest__Output, _mavsdk_rpc_action_DoOrbitResponse__Output>
  GetReturnToLaunchAltitude: MethodDefinition<_mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse, _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest__Output, _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>
  GetTakeoffAltitude: MethodDefinition<_mavsdk_rpc_action_GetTakeoffAltitudeRequest, _mavsdk_rpc_action_GetTakeoffAltitudeResponse, _mavsdk_rpc_action_GetTakeoffAltitudeRequest__Output, _mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>
  GotoLocation: MethodDefinition<_mavsdk_rpc_action_GotoLocationRequest, _mavsdk_rpc_action_GotoLocationResponse, _mavsdk_rpc_action_GotoLocationRequest__Output, _mavsdk_rpc_action_GotoLocationResponse__Output>
  GotoLocationFixedwing: MethodDefinition<_mavsdk_rpc_action_GotoLocationFixedwingRequest, _mavsdk_rpc_action_GotoLocationFixedwingResponse, _mavsdk_rpc_action_GotoLocationFixedwingRequest__Output, _mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>
  Hold: MethodDefinition<_mavsdk_rpc_action_HoldRequest, _mavsdk_rpc_action_HoldResponse, _mavsdk_rpc_action_HoldRequest__Output, _mavsdk_rpc_action_HoldResponse__Output>
  Kill: MethodDefinition<_mavsdk_rpc_action_KillRequest, _mavsdk_rpc_action_KillResponse, _mavsdk_rpc_action_KillRequest__Output, _mavsdk_rpc_action_KillResponse__Output>
  Land: MethodDefinition<_mavsdk_rpc_action_LandRequest, _mavsdk_rpc_action_LandResponse, _mavsdk_rpc_action_LandRequest__Output, _mavsdk_rpc_action_LandResponse__Output>
  Reboot: MethodDefinition<_mavsdk_rpc_action_RebootRequest, _mavsdk_rpc_action_RebootResponse, _mavsdk_rpc_action_RebootRequest__Output, _mavsdk_rpc_action_RebootResponse__Output>
  ReturnToLaunch: MethodDefinition<_mavsdk_rpc_action_ReturnToLaunchRequest, _mavsdk_rpc_action_ReturnToLaunchResponse, _mavsdk_rpc_action_ReturnToLaunchRequest__Output, _mavsdk_rpc_action_ReturnToLaunchResponse__Output>
  SetActuator: MethodDefinition<_mavsdk_rpc_action_SetActuatorRequest, _mavsdk_rpc_action_SetActuatorResponse, _mavsdk_rpc_action_SetActuatorRequest__Output, _mavsdk_rpc_action_SetActuatorResponse__Output>
  SetCurrentSpeed: MethodDefinition<_mavsdk_rpc_action_SetCurrentSpeedRequest, _mavsdk_rpc_action_SetCurrentSpeedResponse, _mavsdk_rpc_action_SetCurrentSpeedRequest__Output, _mavsdk_rpc_action_SetCurrentSpeedResponse__Output>
  SetGpsGlobalOrigin: MethodDefinition<_mavsdk_rpc_action_SetGpsGlobalOriginRequest, _mavsdk_rpc_action_SetGpsGlobalOriginResponse, _mavsdk_rpc_action_SetGpsGlobalOriginRequest__Output, _mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>
  SetHome: MethodDefinition<_mavsdk_rpc_action_SetHomeRequest, _mavsdk_rpc_action_SetHomeResponse, _mavsdk_rpc_action_SetHomeRequest__Output, _mavsdk_rpc_action_SetHomeResponse__Output>
  SetRelay: MethodDefinition<_mavsdk_rpc_action_SetRelayRequest, _mavsdk_rpc_action_SetRelayResponse, _mavsdk_rpc_action_SetRelayRequest__Output, _mavsdk_rpc_action_SetRelayResponse__Output>
  SetReturnToLaunchAltitude: MethodDefinition<_mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse, _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest__Output, _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>
  SetTakeoffAltitude: MethodDefinition<_mavsdk_rpc_action_SetTakeoffAltitudeRequest, _mavsdk_rpc_action_SetTakeoffAltitudeResponse, _mavsdk_rpc_action_SetTakeoffAltitudeRequest__Output, _mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>
  Shutdown: MethodDefinition<_mavsdk_rpc_action_ShutdownRequest, _mavsdk_rpc_action_ShutdownResponse, _mavsdk_rpc_action_ShutdownRequest__Output, _mavsdk_rpc_action_ShutdownResponse__Output>
  Takeoff: MethodDefinition<_mavsdk_rpc_action_TakeoffRequest, _mavsdk_rpc_action_TakeoffResponse, _mavsdk_rpc_action_TakeoffRequest__Output, _mavsdk_rpc_action_TakeoffResponse__Output>
  Terminate: MethodDefinition<_mavsdk_rpc_action_TerminateRequest, _mavsdk_rpc_action_TerminateResponse, _mavsdk_rpc_action_TerminateRequest__Output, _mavsdk_rpc_action_TerminateResponse__Output>
  TransitionToFixedwing: MethodDefinition<_mavsdk_rpc_action_TransitionToFixedwingRequest, _mavsdk_rpc_action_TransitionToFixedwingResponse, _mavsdk_rpc_action_TransitionToFixedwingRequest__Output, _mavsdk_rpc_action_TransitionToFixedwingResponse__Output>
  TransitionToMulticopter: MethodDefinition<_mavsdk_rpc_action_TransitionToMulticopterRequest, _mavsdk_rpc_action_TransitionToMulticopterResponse, _mavsdk_rpc_action_TransitionToMulticopterRequest__Output, _mavsdk_rpc_action_TransitionToMulticopterResponse__Output>
}
