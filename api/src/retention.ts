import {mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import {workerRequest,type Jobs} from '@robotics-runtime/host';
import {redactDiagnostics} from './diagnostics.mjs';
import type {Upload} from './uploads.js';
export interface RetentionConfiguration {
 root:string;bucket:string;maximumBytes:number;environment:Readonly<Record<string,string>>;
 keyPath:string;publicKeyPath:string;signingConfiguration:string;trustedRoot:string;
}
export interface Proof {role:string;raw:Buffer;sha256:string}
export class Retention {
 constructor(readonly jobs:Jobs,readonly configuration:RetentionConfiguration){
  if(!configuration.root.startsWith('/'))throw new Error('absolute server retention root required');
  for(const path of [configuration.keyPath,configuration.publicKeyPath,configuration.signingConfiguration,configuration.trustedRoot])
   if(!path.startsWith('/'))throw new Error('fixed absolute custody policy paths required');
 }
 private async operation(uploadId:string,operation:string,executable:string,args:readonly string[],signal:AbortSignal){
  const privateValues=[this.configuration.environment.COSIGN_PASSWORD??''];
  let result;
  try{result=await this.jobs.run(workerRequest({executable,env:this.configuration.environment,extendEnv:false},args,
   {timeoutMs:45000,maxBufferBytes:1048576,cancelSignal:signal}));
  }catch(error){
   console.error(JSON.stringify({kind:'custody-operation-refused',uploadId,operation,executable,
    thrownName:error instanceof Error?error.name:'unknown',thrownCode:error instanceof Error&&'code'in error?String(error.code):null}));
   throw error;
  }
  if(!result.ok){
   console.error(JSON.stringify({kind:'custody-operation-refused',uploadId,operation,executable,
    exitCode:result.exitCode??null,signal:result.signal??null,timedOut:result.timedOut,canceled:result.canceled,code:result.code??null,durationMs:result.durationMs,
    stdout:redactDiagnostics(result.stdout,privateValues).slice(0,8192),stderr:redactDiagnostics(result.stderr,privateValues).slice(0,8192)}));
   throw new Error('custody worker refused',{cause:result});
  }
  return result.stdout;
 }
 async retain(upload:Upload,signal:AbortSignal):Promise<Proof[]>{
  if(!upload.version_id)throw new Error('immutable version must be committed before custody');
  const root=resolve(this.configuration.root);await mkdir(root,{recursive:true,mode:0o700});
  const work=join(root,randomUUID());await mkdir(work,{mode:0o700});
  const source=join(work,'payload'),registration=join(work,'registration.json'),predicate=join(work,'predicate.json');
  const bundle=join(work,'retention.sigstore.json'),verified=join(work,'verified'),receipt=join(work,'receipt.json'),template=join(work,'receipt-template.json');
  const size=Number(upload.size_bytes);
  if(!Number.isSafeInteger(size)||size<0||size>this.configuration.maximumBytes)throw new Error('artifact exceeds selected byte limit');
  try{
   // Internal transport registration; public subject documents are only written by installed CLIs.
   await writeFile(registration,JSON.stringify({upload_status:'confirmed',run_id:'run-'+upload.job_id,
    sha256:upload.checksum,size_bytes:size,media_type:upload.media_type,version_id:upload.version_id,
    uri:'s3://'+this.configuration.bucket+'/'+upload.object_key.split('/').map(encodeURIComponent).join('/')})+'\n',{flag:'wx',mode:0o600});
   await this.operation(upload.id,'download','/usr/local/bin/aws',['s3api','get-object','--bucket',this.configuration.bucket,'--key',upload.object_key,
    '--version-id',upload.version_id,...(size?['--range','bytes=0-'+size]:[]),'--output','json','--no-cli-pager',source],signal);
   const predicateBytes=await this.operation(upload.id,'predicate','/usr/local/bin/retained-artifact',['predicate','--registration',registration,'--source',source],signal);
   await writeFile(predicate,predicateBytes,{flag:'wx',mode:0o600});
   await this.operation(upload.id,'sign','/usr/local/bin/cosign',['attest-blob','--yes','--key',this.configuration.keyPath,
    '--signing-config',this.configuration.signingConfiguration,'--trusted-root',this.configuration.trustedRoot,
    '--predicate',predicate,'--type','https://robotics-runtime.dev/attestations/artifact-retention/v1','--bundle',bundle,source],signal);
   await this.operation(upload.id,'verify','/usr/local/bin/retained-artifact',['verify','--registration',registration,'--bundle',bundle,
    '--key',this.configuration.publicKeyPath,'--output',verified,'--max-artifact-bytes',String(this.configuration.maximumBytes)],signal);
   await writeFile(template,JSON.stringify({receipt_id:'receipt-'+upload.id,run_id:'run-'+upload.job_id,created_at:new Date().toISOString()})+'\n',{flag:'wx',mode:0o600});
   await this.operation(upload.id,'receipt','/opt/venv/bin/robotics-contracts',['--format','json','artifact-receipt','create','--template',template,
    '--source',source,'--verification',join(verified,'artifact-verification.json'),'--dependency',join(verified,'statement.json'),
    '--dependency',join(verified,'trust-policy.pem'),'--dependency',join(verified,'verification-evidence.sigstore.json'),'--output',receipt],signal);
   const files=[['receipt',receipt],['verification',join(verified,'artifact-verification.json')],['statement',join(verified,'statement.json')],
    ['trust-policy',join(verified,'trust-policy.pem')],['signature',join(verified,'verification-evidence.sigstore.json')]];
   return await Promise.all(files.map(async([role,path])=>{const raw=await readFile(path);return{role,raw,sha256:createHash('sha256').update(raw).digest('hex')}}));
  }finally{
   // This directory is generated beneath the fixed server root; it contains only this settled finite attempt.
   if(resolve(work).startsWith(root+'/'))await rm(work,{recursive:true,force:true});
  }
 }
}
