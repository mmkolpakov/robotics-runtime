import {writeFile,mkdir,readFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';

export function redactDiagnostics(raw,privateValues=[]){
 let safe=raw;
 for(const value of privateValues)if(value.length>=8)safe=safe.split(value).join('[redacted]');
 safe=safe.replace(/\b(?:https?|postgres(?:ql)?|s3):\/\/[^\s"'<>]+/gi,text=>{
  try{const url=new URL(text);url.username='';url.password='';url.search=url.search?'?[redacted-query]':'';return url.toString()}
  catch{return '[redacted-url]'}
 });
 safe=safe.replace(/(\bauthorization["']?\s*[:=]\s*["']?)[^\r\n]*/gi,'$1[redacted]');
 safe=safe.replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi,'Bearer [redacted]');
 safe=safe.replace(/\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g,'[redacted-jwt]');
 safe=safe.replace(/((?:client_secret|access_token|aws_secret_access_key|aws_access_key_id|aws_session_token|cosign_password|password)["']?\s*[:=]\s*["']?)[^\s"',;}]+/gi,'$1[redacted]');
 return Buffer.from(safe).subarray(-65536).toString('utf8');
}
export function assertSafeArtifact(raw,privateValues=[]){
 const text=raw.toString('utf8');
 if(privateValues.some(value=>value.length>=8&&text.includes(value))||
  /\bBearer\s+(?!\[redacted\])[A-Za-z0-9._~+/=-]+|\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b|X-Amz-(?:Signature|Credential|Security-Token)=|(?:client_secret|access_token)=(?!\[redacted\])/i.test(text))
  throw new Error('artifact contains diagnostic authority; public retention refused');
}
export async function retainDiagnostic(directory,name,raw,privateValues=[]){
 if(!['consumer-failure.log','api-failure.log'].includes(name))throw new Error('fixed diagnostic name required');
 const safe=Buffer.from(redactDiagnostics(raw,privateValues));assertSafeArtifact(safe,privateValues);
 await writeFile(join(directory,name),safe);
}
export async function publishSafeFiles(source,destination,files,privateValues=[]){
 const base=resolve(source),target=resolve(destination),manifest=[];
 const checked=[];
 for(const name of files){
  const from=resolve(base,name),to=resolve(target,name);
  if(!from.startsWith(base+'/')||!to.startsWith(target+'/'))throw new Error('safe closure path refused');
  const raw=await readFile(from);assertSafeArtifact(raw,privateValues);checked.push({name,to,raw});
 }
 for(const {name,to,raw}of checked){await mkdir(resolve(to,'..'),{recursive:true});await writeFile(to,raw);manifest.push({path:name,size:raw.length,sha256:createHash('sha256').update(raw).digest('hex')})}
 await mkdir(target,{recursive:true});await writeFile(join(target,'safe-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
}
