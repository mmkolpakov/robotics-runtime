import {S3Client,PutObjectCommand,HeadObjectCommand,GetBucketVersioningCommand} from '@aws-sdk/client-s3';
import {getSignedUrl} from '@aws-sdk/s3-request-presigner';
import {ApiError} from './database.js';
export const EXISTING_ARTIFACT_MAX_BYTES=1073741824;
export interface Upload {id:string;job_id:string;object_key:string;checksum:string;size_bytes:string;media_type:string;version_id:string|null}
export class UploadStorage {
 readonly client:S3Client;
 constructor(readonly bucket:string,endpoint:string,region:string,readonly maximumBytes:number){
  if(!Number.isSafeInteger(maximumBytes)||maximumBytes<1||maximumBytes>EXISTING_ARTIFACT_MAX_BYTES)throw new Error('invalid artifact byte limit');
  if(!/^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$/.test(bucket))throw new Error('invalid configured bucket');
  const url=new URL(endpoint);if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw new Error('invalid configured S3 endpoint');
  this.client=new S3Client({endpoint,region,forcePathStyle:true,requestChecksumCalculation:'WHEN_REQUIRED'});
 }
 size(value:number){if(!Number.isSafeInteger(value)||value<0||value>this.maximumBytes)throw new ApiError(400,'artifact exceeds selected byte limit')}
 async presign(upload:Upload){
  const size=Number(upload.size_bytes);this.size(size);
  const checksum=Buffer.from(upload.checksum,'hex').toString('base64');
  const command=new PutObjectCommand({Bucket:this.bucket,Key:upload.object_key,ContentLength:size,ContentType:upload.media_type,
   ChecksumAlgorithm:'SHA256',ChecksumSHA256:checksum,Metadata:{'upload-id':upload.id,'run-id':'run-'+upload.job_id,sha256:upload.checksum}});
  const url=await getSignedUrl(this.client,command,{expiresIn:120,unhoistableHeaders:new Set(['x-amz-checksum-sha256','x-amz-meta-upload-id','x-amz-meta-run-id','x-amz-meta-sha256']),
   signableHeaders:new Set(['content-type','content-length'])});
  return {logID:upload.id,uploadURL:url,requiredHeaders:{'Content-Type':upload.media_type,'x-amz-checksum-sha256':checksum,'x-amz-meta-upload-id':upload.id,'x-amz-meta-run-id':'run-'+upload.job_id,'x-amz-meta-sha256':upload.checksum}};
 }
 async version(upload:Upload,signal:AbortSignal){
  const size=Number(upload.size_bytes);this.size(size);
  const head=await this.client.send(new HeadObjectCommand({Bucket:this.bucket,Key:upload.object_key,
   ...(upload.version_id?{VersionId:upload.version_id}:{}),ChecksumMode:'ENABLED'}),{abortSignal:signal});
  if(!head.VersionId||head.VersionId==='null'||(upload.version_id!==null&&head.VersionId!==upload.version_id)||head.ContentLength!==size||head.ContentType!==upload.media_type||
   head.ChecksumSHA256!==Buffer.from(upload.checksum,'hex').toString('base64')||
   head.Metadata?.['upload-id']!==upload.id||head.Metadata?.['run-id']!=='run-'+upload.job_id||head.Metadata?.sha256!==upload.checksum)
   throw new ApiError(409,'uploaded object does not match its registered identity');
  return head.VersionId;
 }
 async ready(){const response=await this.client.send(new GetBucketVersioningCommand({Bucket:this.bucket}),{abortSignal:AbortSignal.timeout(15000)});if(response.Status!=='Enabled')throw new Error('versioned evidence bucket required')}
 close(){this.client.destroy()}
}
export function mediaType(fileName:string,logType:string){
 if(logType==='EMISSIONS_LOG')return 'application/x-ndjson';
 if(fileName.endsWith('.png'))return 'image/png';
 if(fileName.endsWith('.jsonl'))return 'application/x-ndjson';
 if(fileName.endsWith('.json'))return 'application/json';
 return 'text/plain';
}
