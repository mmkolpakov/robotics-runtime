import {createHash} from 'node:crypto';
import {ApiError} from './database.js';
export const CONFIG_MAX_BYTES=262144,TEMPLATE_MAX_BYTES=65536,TEMPLATE_MAX_COUNT=32,CONFIG_TOTAL_MAX_BYTES=524288;
export interface MetricsTemplate {name:string;contents:string}
export interface MetricsConfigInput {projectId:string;config:string;templateFiles:MetricsTemplate[];branch?:string|null}
const digest=(bytes:Buffer)=>createHash('sha256').update(bytes).digest('hex');
function decode(value:string,maximum:number):Buffer{
 if(typeof value!=='string'||value.length>4*Math.ceil(maximum/3)||value.length%4!==0||! /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value))throw new ApiError(400,'invalid bounded base64 payload');
 const bytes=Buffer.from(value,'base64');
 if(bytes.length>maximum||bytes.toString('base64')!==value)throw new ApiError(400,'invalid bounded base64 payload');
 return bytes;
}
export function metricsConfigBytes(input:MetricsConfigInput){
 if(!Array.isArray(input.templateFiles)||input.templateFiles.length>TEMPLATE_MAX_COUNT)throw new ApiError(400,'template count exceeds recipe');
 const config=decode(input.config,CONFIG_MAX_BYTES);let total=config.length;const names=new Set<string>();
 const templates=input.templateFiles.map(file=>{
  if(typeof file.name!=='string'||file.name.length<1||file.name.length>255||/[\\/\u0000-\u001f\u007f]/.test(file.name)||!file.name.toLowerCase().endsWith('.liquid')||names.has(file.name))throw new ApiError(400,'invalid or duplicate template basename');
  names.add(file.name);const bytes=decode(file.contents,TEMPLATE_MAX_BYTES);total+=bytes.length;
  if(total>CONFIG_TOTAL_MAX_BYTES)throw new ApiError(400,'combined config bytes exceed recipe');
  return {name:file.name,contents:bytes.toString('base64'),sha256:digest(bytes),size:bytes.length};
 }).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
 const configSha256=digest(config);
 const identity=JSON.stringify({config:{sha256:configSha256,size:config.length},templates:templates.map(({name,sha256,size})=>({name,sha256,size}))});
 return {config,configSha256,templates,snapshotSha256:digest(Buffer.from(identity))};
}
