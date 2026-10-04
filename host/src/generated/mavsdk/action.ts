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
import type { ActionResult as _mavsdk_rpc_action_ActionResult, ActionResult__Output as _mavsdk_rpc_action_ActionResult__Output } from './mavsdk/rpc/action/ActionResult.js';
import type { ActionServiceClient as _mavsdk_rpc_action_ActionServiceClient, ActionServiceDefinition as _mavsdk_rpc_action_ActionServiceDefinition } from './mavsdk/rpc/action/ActionService.js';
import type { ArmForceRequest as _mavsdk_rpc_action_ArmForceRequest, ArmForceRequest__Output as _mavsdk_rpc_action_ArmForceRequest__Output } from './mavsdk/rpc/action/ArmForceRequest.js';
import type { ArmForceResponse as _mavsdk_rpc_action_ArmForceResponse, ArmForceResponse__Output as _mavsdk_rpc_action_ArmForceResponse__Output } from './mavsdk/rpc/action/ArmForceResponse.js';
import type { ArmRequest as _mavsdk_rpc_action_ArmRequest, ArmRequest__Output as _mavsdk_rpc_action_ArmRequest__Output } from './mavsdk/rpc/action/ArmRequest.js';
import type { ArmResponse as _mavsdk_rpc_action_ArmResponse, ArmResponse__Output as _mavsdk_rpc_action_ArmResponse__Output } from './mavsdk/rpc/action/ArmResponse.js';
import type { DisarmRequest as _mavsdk_rpc_action_DisarmRequest, DisarmRequest__Output as _mavsdk_rpc_action_DisarmRequest__Output } from './mavsdk/rpc/action/DisarmRequest.js';
import type { DisarmResponse as _mavsdk_rpc_action_DisarmResponse, DisarmResponse__Output as _mavsdk_rpc_action_DisarmResponse__Output } from './mavsdk/rpc/action/DisarmResponse.js';
import type { DoOrbitRequest as _mavsdk_rpc_action_DoOrbitRequest, DoOrbitRequest__Output as _mavsdk_rpc_action_DoOrbitRequest__Output } from './mavsdk/rpc/action/DoOrbitRequest.js';
import type { DoOrbitResponse as _mavsdk_rpc_action_DoOrbitResponse, DoOrbitResponse__Output as _mavsdk_rpc_action_DoOrbitResponse__Output } from './mavsdk/rpc/action/DoOrbitResponse.js';
import type { GetReturnToLaunchAltitudeRequest as _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, GetReturnToLaunchAltitudeRequest__Output as _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest__Output } from './mavsdk/rpc/action/GetReturnToLaunchAltitudeRequest.js';
import type { GetReturnToLaunchAltitudeResponse as _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse, GetReturnToLaunchAltitudeResponse__Output as _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output } from './mavsdk/rpc/action/GetReturnToLaunchAltitudeResponse.js';
import type { GetTakeoffAltitudeRequest as _mavsdk_rpc_action_GetTakeoffAltitudeRequest, GetTakeoffAltitudeRequest__Output as _mavsdk_rpc_action_GetTakeoffAltitudeRequest__Output } from './mavsdk/rpc/action/GetTakeoffAltitudeRequest.js';
import type { GetTakeoffAltitudeResponse as _mavsdk_rpc_action_GetTakeoffAltitudeResponse, GetTakeoffAltitudeResponse__Output as _mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output } from './mavsdk/rpc/action/GetTakeoffAltitudeResponse.js';
import type { GotoLocationFixedwingRequest as _mavsdk_rpc_action_GotoLocationFixedwingRequest, GotoLocationFixedwingRequest__Output as _mavsdk_rpc_action_GotoLocationFixedwingRequest__Output } from './mavsdk/rpc/action/GotoLocationFixedwingRequest.js';
import type { GotoLocationFixedwingResponse as _mavsdk_rpc_action_GotoLocationFixedwingResponse, GotoLocationFixedwingResponse__Output as _mavsdk_rpc_action_GotoLocationFixedwingResponse__Output } from './mavsdk/rpc/action/GotoLocationFixedwingResponse.js';
import type { GotoLocationRequest as _mavsdk_rpc_action_GotoLocationRequest, GotoLocationRequest__Output as _mavsdk_rpc_action_GotoLocationRequest__Output } from './mavsdk/rpc/action/GotoLocationRequest.js';
import type { GotoLocationResponse as _mavsdk_rpc_action_GotoLocationResponse, GotoLocationResponse__Output as _mavsdk_rpc_action_GotoLocationResponse__Output } from './mavsdk/rpc/action/GotoLocationResponse.js';
import type { HoldRequest as _mavsdk_rpc_action_HoldRequest, HoldRequest__Output as _mavsdk_rpc_action_HoldRequest__Output } from './mavsdk/rpc/action/HoldRequest.js';
import type { HoldResponse as _mavsdk_rpc_action_HoldResponse, HoldResponse__Output as _mavsdk_rpc_action_HoldResponse__Output } from './mavsdk/rpc/action/HoldResponse.js';
import type { KillRequest as _mavsdk_rpc_action_KillRequest, KillRequest__Output as _mavsdk_rpc_action_KillRequest__Output } from './mavsdk/rpc/action/KillRequest.js';
import type { KillResponse as _mavsdk_rpc_action_KillResponse, KillResponse__Output as _mavsdk_rpc_action_KillResponse__Output } from './mavsdk/rpc/action/KillResponse.js';
import type { LandRequest as _mavsdk_rpc_action_LandRequest, LandRequest__Output as _mavsdk_rpc_action_LandRequest__Output } from './mavsdk/rpc/action/LandRequest.js';
import type { LandResponse as _mavsdk_rpc_action_LandResponse, LandResponse__Output as _mavsdk_rpc_action_LandResponse__Output } from './mavsdk/rpc/action/LandResponse.js';
import type { RebootRequest as _mavsdk_rpc_action_RebootRequest, RebootRequest__Output as _mavsdk_rpc_action_RebootRequest__Output } from './mavsdk/rpc/action/RebootRequest.js';
import type { RebootResponse as _mavsdk_rpc_action_RebootResponse, RebootResponse__Output as _mavsdk_rpc_action_RebootResponse__Output } from './mavsdk/rpc/action/RebootResponse.js';
import type { ReturnToLaunchRequest as _mavsdk_rpc_action_ReturnToLaunchRequest, ReturnToLaunchRequest__Output as _mavsdk_rpc_action_ReturnToLaunchRequest__Output } from './mavsdk/rpc/action/ReturnToLaunchRequest.js';
import type { ReturnToLaunchResponse as _mavsdk_rpc_action_ReturnToLaunchResponse, ReturnToLaunchResponse__Output as _mavsdk_rpc_action_ReturnToLaunchResponse__Output } from './mavsdk/rpc/action/ReturnToLaunchResponse.js';
import type { SetActuatorRequest as _mavsdk_rpc_action_SetActuatorRequest, SetActuatorRequest__Output as _mavsdk_rpc_action_SetActuatorRequest__Output } from './mavsdk/rpc/action/SetActuatorRequest.js';
import type { SetActuatorResponse as _mavsdk_rpc_action_SetActuatorResponse, SetActuatorResponse__Output as _mavsdk_rpc_action_SetActuatorResponse__Output } from './mavsdk/rpc/action/SetActuatorResponse.js';
import type { SetCurrentSpeedRequest as _mavsdk_rpc_action_SetCurrentSpeedRequest, SetCurrentSpeedRequest__Output as _mavsdk_rpc_action_SetCurrentSpeedRequest__Output } from './mavsdk/rpc/action/SetCurrentSpeedRequest.js';
import type { SetCurrentSpeedResponse as _mavsdk_rpc_action_SetCurrentSpeedResponse, SetCurrentSpeedResponse__Output as _mavsdk_rpc_action_SetCurrentSpeedResponse__Output } from './mavsdk/rpc/action/SetCurrentSpeedResponse.js';
import type { SetGpsGlobalOriginRequest as _mavsdk_rpc_action_SetGpsGlobalOriginRequest, SetGpsGlobalOriginRequest__Output as _mavsdk_rpc_action_SetGpsGlobalOriginRequest__Output } from './mavsdk/rpc/action/SetGpsGlobalOriginRequest.js';
import type { SetGpsGlobalOriginResponse as _mavsdk_rpc_action_SetGpsGlobalOriginResponse, SetGpsGlobalOriginResponse__Output as _mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output } from './mavsdk/rpc/action/SetGpsGlobalOriginResponse.js';
import type { SetHomeRequest as _mavsdk_rpc_action_SetHomeRequest, SetHomeRequest__Output as _mavsdk_rpc_action_SetHomeRequest__Output } from './mavsdk/rpc/action/SetHomeRequest.js';
import type { SetHomeResponse as _mavsdk_rpc_action_SetHomeResponse, SetHomeResponse__Output as _mavsdk_rpc_action_SetHomeResponse__Output } from './mavsdk/rpc/action/SetHomeResponse.js';
import type { SetRelayRequest as _mavsdk_rpc_action_SetRelayRequest, SetRelayRequest__Output as _mavsdk_rpc_action_SetRelayRequest__Output } from './mavsdk/rpc/action/SetRelayRequest.js';
import type { SetRelayResponse as _mavsdk_rpc_action_SetRelayResponse, SetRelayResponse__Output as _mavsdk_rpc_action_SetRelayResponse__Output } from './mavsdk/rpc/action/SetRelayResponse.js';
import type { SetReturnToLaunchAltitudeRequest as _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, SetReturnToLaunchAltitudeRequest__Output as _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest__Output } from './mavsdk/rpc/action/SetReturnToLaunchAltitudeRequest.js';
import type { SetReturnToLaunchAltitudeResponse as _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse, SetReturnToLaunchAltitudeResponse__Output as _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output } from './mavsdk/rpc/action/SetReturnToLaunchAltitudeResponse.js';
import type { SetTakeoffAltitudeRequest as _mavsdk_rpc_action_SetTakeoffAltitudeRequest, SetTakeoffAltitudeRequest__Output as _mavsdk_rpc_action_SetTakeoffAltitudeRequest__Output } from './mavsdk/rpc/action/SetTakeoffAltitudeRequest.js';
import type { SetTakeoffAltitudeResponse as _mavsdk_rpc_action_SetTakeoffAltitudeResponse, SetTakeoffAltitudeResponse__Output as _mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output } from './mavsdk/rpc/action/SetTakeoffAltitudeResponse.js';
import type { ShutdownRequest as _mavsdk_rpc_action_ShutdownRequest, ShutdownRequest__Output as _mavsdk_rpc_action_ShutdownRequest__Output } from './mavsdk/rpc/action/ShutdownRequest.js';
import type { ShutdownResponse as _mavsdk_rpc_action_ShutdownResponse, ShutdownResponse__Output as _mavsdk_rpc_action_ShutdownResponse__Output } from './mavsdk/rpc/action/ShutdownResponse.js';
import type { TakeoffRequest as _mavsdk_rpc_action_TakeoffRequest, TakeoffRequest__Output as _mavsdk_rpc_action_TakeoffRequest__Output } from './mavsdk/rpc/action/TakeoffRequest.js';
import type { TakeoffResponse as _mavsdk_rpc_action_TakeoffResponse, TakeoffResponse__Output as _mavsdk_rpc_action_TakeoffResponse__Output } from './mavsdk/rpc/action/TakeoffResponse.js';
import type { TerminateRequest as _mavsdk_rpc_action_TerminateRequest, TerminateRequest__Output as _mavsdk_rpc_action_TerminateRequest__Output } from './mavsdk/rpc/action/TerminateRequest.js';
import type { TerminateResponse as _mavsdk_rpc_action_TerminateResponse, TerminateResponse__Output as _mavsdk_rpc_action_TerminateResponse__Output } from './mavsdk/rpc/action/TerminateResponse.js';
import type { TransitionToFixedwingRequest as _mavsdk_rpc_action_TransitionToFixedwingRequest, TransitionToFixedwingRequest__Output as _mavsdk_rpc_action_TransitionToFixedwingRequest__Output } from './mavsdk/rpc/action/TransitionToFixedwingRequest.js';
import type { TransitionToFixedwingResponse as _mavsdk_rpc_action_TransitionToFixedwingResponse, TransitionToFixedwingResponse__Output as _mavsdk_rpc_action_TransitionToFixedwingResponse__Output } from './mavsdk/rpc/action/TransitionToFixedwingResponse.js';
import type { TransitionToMulticopterRequest as _mavsdk_rpc_action_TransitionToMulticopterRequest, TransitionToMulticopterRequest__Output as _mavsdk_rpc_action_TransitionToMulticopterRequest__Output } from './mavsdk/rpc/action/TransitionToMulticopterRequest.js';
import type { TransitionToMulticopterResponse as _mavsdk_rpc_action_TransitionToMulticopterResponse, TransitionToMulticopterResponse__Output as _mavsdk_rpc_action_TransitionToMulticopterResponse__Output } from './mavsdk/rpc/action/TransitionToMulticopterResponse.js';

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
      action: {
        ActionResult: MessageTypeDefinition<_mavsdk_rpc_action_ActionResult, _mavsdk_rpc_action_ActionResult__Output>
        ActionService: SubtypeConstructor<typeof grpc.Client, _mavsdk_rpc_action_ActionServiceClient> & { service: _mavsdk_rpc_action_ActionServiceDefinition }
        ArmForceRequest: MessageTypeDefinition<_mavsdk_rpc_action_ArmForceRequest, _mavsdk_rpc_action_ArmForceRequest__Output>
        ArmForceResponse: MessageTypeDefinition<_mavsdk_rpc_action_ArmForceResponse, _mavsdk_rpc_action_ArmForceResponse__Output>
        ArmRequest: MessageTypeDefinition<_mavsdk_rpc_action_ArmRequest, _mavsdk_rpc_action_ArmRequest__Output>
        ArmResponse: MessageTypeDefinition<_mavsdk_rpc_action_ArmResponse, _mavsdk_rpc_action_ArmResponse__Output>
        DisarmRequest: MessageTypeDefinition<_mavsdk_rpc_action_DisarmRequest, _mavsdk_rpc_action_DisarmRequest__Output>
        DisarmResponse: MessageTypeDefinition<_mavsdk_rpc_action_DisarmResponse, _mavsdk_rpc_action_DisarmResponse__Output>
        DoOrbitRequest: MessageTypeDefinition<_mavsdk_rpc_action_DoOrbitRequest, _mavsdk_rpc_action_DoOrbitRequest__Output>
        DoOrbitResponse: MessageTypeDefinition<_mavsdk_rpc_action_DoOrbitResponse, _mavsdk_rpc_action_DoOrbitResponse__Output>
        GetReturnToLaunchAltitudeRequest: MessageTypeDefinition<_mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest, _mavsdk_rpc_action_GetReturnToLaunchAltitudeRequest__Output>
        GetReturnToLaunchAltitudeResponse: MessageTypeDefinition<_mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse, _mavsdk_rpc_action_GetReturnToLaunchAltitudeResponse__Output>
        GetTakeoffAltitudeRequest: MessageTypeDefinition<_mavsdk_rpc_action_GetTakeoffAltitudeRequest, _mavsdk_rpc_action_GetTakeoffAltitudeRequest__Output>
        GetTakeoffAltitudeResponse: MessageTypeDefinition<_mavsdk_rpc_action_GetTakeoffAltitudeResponse, _mavsdk_rpc_action_GetTakeoffAltitudeResponse__Output>
        GotoLocationFixedwingRequest: MessageTypeDefinition<_mavsdk_rpc_action_GotoLocationFixedwingRequest, _mavsdk_rpc_action_GotoLocationFixedwingRequest__Output>
        GotoLocationFixedwingResponse: MessageTypeDefinition<_mavsdk_rpc_action_GotoLocationFixedwingResponse, _mavsdk_rpc_action_GotoLocationFixedwingResponse__Output>
        GotoLocationRequest: MessageTypeDefinition<_mavsdk_rpc_action_GotoLocationRequest, _mavsdk_rpc_action_GotoLocationRequest__Output>
        GotoLocationResponse: MessageTypeDefinition<_mavsdk_rpc_action_GotoLocationResponse, _mavsdk_rpc_action_GotoLocationResponse__Output>
        HoldRequest: MessageTypeDefinition<_mavsdk_rpc_action_HoldRequest, _mavsdk_rpc_action_HoldRequest__Output>
        HoldResponse: MessageTypeDefinition<_mavsdk_rpc_action_HoldResponse, _mavsdk_rpc_action_HoldResponse__Output>
        KillRequest: MessageTypeDefinition<_mavsdk_rpc_action_KillRequest, _mavsdk_rpc_action_KillRequest__Output>
        KillResponse: MessageTypeDefinition<_mavsdk_rpc_action_KillResponse, _mavsdk_rpc_action_KillResponse__Output>
        LandRequest: MessageTypeDefinition<_mavsdk_rpc_action_LandRequest, _mavsdk_rpc_action_LandRequest__Output>
        LandResponse: MessageTypeDefinition<_mavsdk_rpc_action_LandResponse, _mavsdk_rpc_action_LandResponse__Output>
        OrbitYawBehavior: EnumTypeDefinition
        RebootRequest: MessageTypeDefinition<_mavsdk_rpc_action_RebootRequest, _mavsdk_rpc_action_RebootRequest__Output>
        RebootResponse: MessageTypeDefinition<_mavsdk_rpc_action_RebootResponse, _mavsdk_rpc_action_RebootResponse__Output>
        RelayCommand: EnumTypeDefinition
        ReturnToLaunchRequest: MessageTypeDefinition<_mavsdk_rpc_action_ReturnToLaunchRequest, _mavsdk_rpc_action_ReturnToLaunchRequest__Output>
        ReturnToLaunchResponse: MessageTypeDefinition<_mavsdk_rpc_action_ReturnToLaunchResponse, _mavsdk_rpc_action_ReturnToLaunchResponse__Output>
        SetActuatorRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetActuatorRequest, _mavsdk_rpc_action_SetActuatorRequest__Output>
        SetActuatorResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetActuatorResponse, _mavsdk_rpc_action_SetActuatorResponse__Output>
        SetCurrentSpeedRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetCurrentSpeedRequest, _mavsdk_rpc_action_SetCurrentSpeedRequest__Output>
        SetCurrentSpeedResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetCurrentSpeedResponse, _mavsdk_rpc_action_SetCurrentSpeedResponse__Output>
        SetGpsGlobalOriginRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetGpsGlobalOriginRequest, _mavsdk_rpc_action_SetGpsGlobalOriginRequest__Output>
        SetGpsGlobalOriginResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetGpsGlobalOriginResponse, _mavsdk_rpc_action_SetGpsGlobalOriginResponse__Output>
        SetHomeRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetHomeRequest, _mavsdk_rpc_action_SetHomeRequest__Output>
        SetHomeResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetHomeResponse, _mavsdk_rpc_action_SetHomeResponse__Output>
        SetRelayRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetRelayRequest, _mavsdk_rpc_action_SetRelayRequest__Output>
        SetRelayResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetRelayResponse, _mavsdk_rpc_action_SetRelayResponse__Output>
        SetReturnToLaunchAltitudeRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest, _mavsdk_rpc_action_SetReturnToLaunchAltitudeRequest__Output>
        SetReturnToLaunchAltitudeResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse, _mavsdk_rpc_action_SetReturnToLaunchAltitudeResponse__Output>
        SetTakeoffAltitudeRequest: MessageTypeDefinition<_mavsdk_rpc_action_SetTakeoffAltitudeRequest, _mavsdk_rpc_action_SetTakeoffAltitudeRequest__Output>
        SetTakeoffAltitudeResponse: MessageTypeDefinition<_mavsdk_rpc_action_SetTakeoffAltitudeResponse, _mavsdk_rpc_action_SetTakeoffAltitudeResponse__Output>
        ShutdownRequest: MessageTypeDefinition<_mavsdk_rpc_action_ShutdownRequest, _mavsdk_rpc_action_ShutdownRequest__Output>
        ShutdownResponse: MessageTypeDefinition<_mavsdk_rpc_action_ShutdownResponse, _mavsdk_rpc_action_ShutdownResponse__Output>
        TakeoffRequest: MessageTypeDefinition<_mavsdk_rpc_action_TakeoffRequest, _mavsdk_rpc_action_TakeoffRequest__Output>
        TakeoffResponse: MessageTypeDefinition<_mavsdk_rpc_action_TakeoffResponse, _mavsdk_rpc_action_TakeoffResponse__Output>
        TerminateRequest: MessageTypeDefinition<_mavsdk_rpc_action_TerminateRequest, _mavsdk_rpc_action_TerminateRequest__Output>
        TerminateResponse: MessageTypeDefinition<_mavsdk_rpc_action_TerminateResponse, _mavsdk_rpc_action_TerminateResponse__Output>
        TransitionToFixedwingRequest: MessageTypeDefinition<_mavsdk_rpc_action_TransitionToFixedwingRequest, _mavsdk_rpc_action_TransitionToFixedwingRequest__Output>
        TransitionToFixedwingResponse: MessageTypeDefinition<_mavsdk_rpc_action_TransitionToFixedwingResponse, _mavsdk_rpc_action_TransitionToFixedwingResponse__Output>
        TransitionToMulticopterRequest: MessageTypeDefinition<_mavsdk_rpc_action_TransitionToMulticopterRequest, _mavsdk_rpc_action_TransitionToMulticopterRequest__Output>
        TransitionToMulticopterResponse: MessageTypeDefinition<_mavsdk_rpc_action_TransitionToMulticopterResponse, _mavsdk_rpc_action_TransitionToMulticopterResponse__Output>
      }
    }
  }
}

