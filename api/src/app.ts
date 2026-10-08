import Fastify,{type FastifyInstance,type FastifyError} from 'fastify';
import type {Domain,Addresses} from './domain.js';
import {ApiError} from './database.js';
import {tokenVerifier,type IdentityConfiguration,type Principal} from './identity.js';
declare module 'fastify' {interface FastifyRequest {principal?:Principal;operationSignal?:AbortSignal}}
const uuid={type:'string',pattern:'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'};
const text={type:'string',minLength:1,maxLength:256};
const parameters=(names:string[])=>({type:'object',required:names,additionalProperties:false,properties:Object.fromEntries(names.map(name=>[name,uuid]))});
const body=(properties:Record<string,unknown>,required:string[])=>({type:'object',additionalProperties:false,properties,required});
export function createApi(domain:Domain,identity:IdentityConfiguration):FastifyInstance{
 const api=Fastify({logger:false,bodyLimit:1048576,ajv:{customOptions:{coerceTypes:false,useDefaults:false,removeAdditional:false,allErrors:false}}});
 const verify=tokenVerifier(identity);
 api.addHook('onRequest',async request=>{
  try{request.principal=await verify(request.headers.authorization)}catch{throw new ApiError(401,'authentication required')}
 });
 api.addHook('preValidation',async request=>{
  if(request.method!=='GET'&&Object.keys(request.query as object).length)throw new ApiError(400,'query options are outside this recipe');
 });
 api.addHook('preHandler',async(request,reply)=>{
  const aborted=new AbortController();
  reply.raw.once('close',()=>{if(!reply.raw.writableEnded)aborted.abort(new Error('HTTP caller disconnected'))});
  request.operationSignal=AbortSignal.any([aborted.signal,AbortSignal.timeout(120000)]);
 });
 api.setErrorHandler<FastifyError>((error,request,reply)=>{
  const status=error instanceof ApiError?error.status:error.validation?400:503;
  const message=error instanceof ApiError?error.message:error.validation?'invalid request':'operation incomplete; retry the same registered operation';
  reply.status(status).send({message});
 });
 api.get('/projects/:projectID/branches',{schema:{params:parameters(['projectID']),
  querystring:body({name:text},['name'])}},async request=>{
   const p=request.params as Addresses,q=request.query as {name:string};
   return domain.branches(request.principal!,p.projectID,q.name);
  });
 api.post('/projects/:projectID/batches/light',{schema:{params:parameters(['projectID']),
  body:body({branchID:uuid,batchName:text,version:{type:'string',maxLength:512},metricsSetName:{type:['string','null'],maxLength:256}},['branchID'])}},
  async(request,reply)=>reply.status(201).send(await domain.createBatch(request.principal!,(request.params as Addresses).projectID,request.body as Parameters<Domain['createBatch']>[2])));
 api.post('/projects/:projectID/batches/:batchID/jobs',{schema:{params:parameters(['projectID','batchID']),body:body({name:text},['name'])}},
  async(request,reply)=>reply.status(201).send(await domain.createJob(request.principal!,request.params as Addresses,request.body as {name:string})));
 api.post('/projects/:projectID/batches/:batchID/jobs/:jobID/logs',{schema:{params:parameters(['projectID','batchID','jobID']),
  body:body({fileName:{type:'string',minLength:1,maxLength:255,pattern:'^[^\\u0000-\\u001f]+$'},fileSize:{type:'integer',minimum:0,maximum:domain.storage.maximumBytes},
   checksum:{type:'string',pattern:'^[0-9a-f]{64}$'},logType:{type:'string',enum:['EMISSIONS_LOG','OTHER_LOG','CONTAINER_LOG','SYSTEM_LOG','ERROR_LOG','EXECUTION_LOG']}},
   ['fileName','fileSize','checksum'])}},
  async(request,reply)=>reply.status(201).send(await domain.registerLog(request.principal!,request.params as Addresses,request.body as Parameters<Domain['registerLog']>[2])));
 api.post('/projects/:projectID/batches/:batchID/jobs/:jobID/close',{schema:{params:parameters(['projectID','batchID','jobID']),
  body:body({status:{type:'string',enum:['SUCCEEDED','ERROR']},errorMessage:{type:'string',maxLength:4096}},['status'])}},
  async(request,reply)=>{await domain.closeJob(request.principal!,request.params as Addresses,request.body as Parameters<Domain['closeJob']>[2],request.operationSignal!);return reply.status(204).send()});
 api.post('/projects/:projectID/batches/:batchID/close',{schema:{params:parameters(['projectID','batchID'])},preValidation:async request=>{if(request.body!==undefined)throw new ApiError(400,'batch close accepts no body')}},
  async(request,reply)=>{await domain.closeBatch(request.principal!,request.params as Addresses);return reply.status(204).send()});
 return api;
}
