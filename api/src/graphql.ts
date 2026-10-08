import mercurius,{type MercuriusContext} from 'mercurius';
import {GraphQLError,NoSchemaIntrospectionCustomRule,type ValidationRule} from 'graphql';
import type {FastifyInstance} from 'fastify';
import type {Domain} from './domain.js';
import {ApiError} from './database.js';
import type {Principal} from './identity.js';
import type {MetricsConfigInput} from './metrics-config.js';
declare module 'mercurius' {interface MercuriusContext {principal:Principal;signal:AbortSignal}}
const fieldBound:ValidationRule=context=>{let count=0;return {Field(node){if(++count===65)context.reportError(new GraphQLError('field count exceeds recipe',{nodes:node}))}}};
export function registerMetricsConfig(api:FastifyInstance,domain:Domain){
 api.register(mercurius,{
  schema:`
   input MetricsTemplate { name: String!, contents: String! }
   type Query { _empty: Boolean }
   type Mutation { updateMetricsConfig(projectId: String!, config: String!, templateFiles: [MetricsTemplate!]!, branch: String): Boolean }
  `,
  resolvers:{Query:{_empty:()=>null},Mutation:{updateMetricsConfig:async(_parent:unknown,input:MetricsConfigInput,context:MercuriusContext)=>{
   await domain.updateMetricsConfig(context.principal,input,context.signal);return true;
  }}},
  context:request=>({principal:request.principal!,signal:request.operationSignal!}),
  graphiql:false,subscription:false,allowBatchedQueries:false,jit:0,queryDepth:8,
  graphql:{parseOptions:{maxTokens:2048},validateOptions:{maxErrors:1}},
  validationRules:[NoSchemaIntrospectionCustomRule,fieldBound],
  errorFormatter:(result,context)=>{
   const formatted=mercurius.defaultErrorFormatter(result,context);
   return {statusCode:formatted.statusCode,response:{data:result.data,errors:result.errors.map(error=>({
    message:error.originalError instanceof ApiError?error.originalError.message:error.originalError?'operation incomplete; retry the same config':'invalid GraphQL request',
    ...(error.path?{path:error.path}:{}),...(error.locations?{locations:error.locations}:{})
   }))}};
  }
 });
}
