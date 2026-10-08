import {randomUUID} from 'node:crypto';
import {Pool,type PoolClient} from 'pg';
import {transaction,transactionClient,project,ApiError} from './database.js';
import type {Principal} from './identity.js';
import {UploadStorage,mediaType,type Upload} from './uploads.js';
import {Retention} from './retention.js';
import {projectIdentifier,branchName} from './admission.js';
import {metricsConfigBytes,type MetricsConfigInput} from './metrics-config.js';
export interface Addresses {projectID:string;batchID?:string;jobID?:string}
export class Domain {
 constructor(readonly pool:Pool,readonly storage:UploadStorage,readonly retention:Retention,readonly maximumUploads=64){
  if(!Number.isSafeInteger(maximumUploads)||maximumUploads<1||maximumUploads>4096)throw new Error('invalid registered upload bound');
 }
 private async batch(client:PoolClient,p:{tenant_id:string;id:string},batchID:string,lock=false){
  const value=await client.query('SELECT * FROM api.batches WHERE tenant_id=$1 AND project_id=$2 AND id=$3'+(lock?' FOR UPDATE':''),[p.tenant_id,p.id,batchID]);
  if(value.rows.length!==1)throw new ApiError(404,'batch not found');return value.rows[0];
 }
 private async job(client:PoolClient,p:{tenant_id:string;id:string},batchID:string,jobID:string,lock=false){
  const value=await client.query('SELECT * FROM api.jobs WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND id=$4'+(lock?' FOR UPDATE':''),[p.tenant_id,p.id,batchID,jobID]);
  if(value.rows.length!==1)throw new ApiError(404,'job not found');return value.rows[0];
 }
 branches(principal:Principal,projectID:string,name:string){
  return transaction(this.pool,principal,async client=>{
   const p=await project(client,projectID);
   const found=await client.query('SELECT * FROM api.branches WHERE tenant_id=$1 AND project_id=$2 AND name=$3',[p.tenant_id,p.id,name]);
   return {branches:found.rows.map(row=>({branchID:row.id,name:row.name,projectID:p.id,branchType:row.branch_type,
    creationTimestamp:row.created_at.toISOString(),userID:row.created_by,orgID:p.tenant_id}))};
  });
 }
 async updateMetricsConfig(principal:Principal,input:MetricsConfigInput,signal:AbortSignal){
  const projectID=projectIdentifier(input.projectId),name=branchName(input.branch);
  const bytes=metricsConfigBytes(input);signal.throwIfAborted();
  return transaction(this.pool,principal,async client=>{
   const p=await project(client,projectID);
   const branch=await client.query('SELECT id FROM api.branches WHERE tenant_id=$1 AND project_id=$2 AND name=$3 FOR UPDATE',[p.tenant_id,p.id,name]);
   if(branch.rows.length!==1)throw new ApiError(404,'branch not found');signal.throwIfAborted();
   const branchID=branch.rows[0].id;
   const prior=await client.query('SELECT id FROM api.config_snapshots WHERE tenant_id=$1 AND project_id=$2 AND branch_id=$3 AND snapshot_sha256=$4',[p.tenant_id,p.id,branchID,bytes.snapshotSha256]);
   const id=prior.rows[0]?.id??randomUUID();
   if(!prior.rows.length)await client.query('INSERT INTO api.config_snapshots(tenant_id,project_id,branch_id,id,config,config_sha256,template_files,snapshot_sha256,created_by) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)',
    [p.tenant_id,p.id,branchID,id,bytes.config,bytes.configSha256,JSON.stringify(bytes.templates),bytes.snapshotSha256,p.principal_id]);
   await client.query('UPDATE api.branches SET config_snapshot_id=$4 WHERE tenant_id=$1 AND project_id=$2 AND id=$3',[p.tenant_id,p.id,branchID,id]);
   signal.throwIfAborted();return id;
  });
 }
 createBatch(principal:Principal,projectID:string,input:{branchID:string;batchName?:string;version?:string;metricsSetName?:string|null}){
  if(input.metricsSetName!==undefined&&input.metricsSetName!==null)throw new ApiError(400,'metrics configuration is outside this recipe');
  return transaction(this.pool,principal,async client=>{
   const p=await project(client,projectID);
   const branch=await client.query('SELECT id,config_snapshot_id FROM api.branches WHERE tenant_id=$1 AND project_id=$2 AND id=$3 FOR UPDATE',[p.tenant_id,p.id,input.branchID]);
   if(branch.rows.length!==1)throw new ApiError(404,'branch not found');
   const id=randomUUID(),name=input.batchName??id;
   const found=await client.query('INSERT INTO api.batches(tenant_id,project_id,id,branch_id,name,version,account,created_by,config_snapshot_id) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *',
    [p.tenant_id,p.id,id,input.branchID,name,input.version??null,p.account,p.principal_id,branch.rows[0].config_snapshot_id]);
   const row=found.rows[0];return {associatedAccount:row.account,batchID:id,branchID:row.branch_id,projectID:p.id,
    orgID:p.tenant_id,userID:p.principal_id,friendlyName:name,batchType:'LIGHT',status:'EXPERIENCES_RUNNING',creationTimestamp:row.created_at.toISOString()};
  });
 }
 createJob(principal:Principal,a:Addresses,input:{name:string}){
  return transaction(this.pool,principal,async client=>{
   const p=await project(client,a.projectID),batch=await this.batch(client,p,a.batchID!,true);
   if(batch.closed_at)throw new ApiError(400,'batch is closed');
   const experience=await client.query('INSERT INTO api.experiences(tenant_id,project_id,id,name) VALUES($1,$2,$3,$4) ON CONFLICT(tenant_id,project_id,name) DO UPDATE SET name=EXCLUDED.name RETURNING id',
    [p.tenant_id,p.id,randomUUID(),input.name]);
   const id=randomUUID(),found=await client.query('INSERT INTO api.jobs(tenant_id,project_id,batch_id,id,experience_id,name,created_by) VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING created_at',
    [p.tenant_id,p.id,a.batchID,id,experience.rows[0].id,input.name,p.principal_id]);
   return {jobID:id,experienceID:experience.rows[0].id,experienceName:input.name,projectID:p.id,batchID:a.batchID,
    branchID:batch.branch_id,orgID:p.tenant_id,userID:p.principal_id,jobStatus:'EXPERIENCE_RUNNING',
    creationTimestamp:found.rows[0].created_at.toISOString()};
  });
 }
 async registerLog(principal:Principal,a:Addresses,input:{fileName:string;fileSize:number;checksum:string;logType?:string}){
  this.storage.size(input.fileSize);
  const upload=await transaction(this.pool,principal,async client=>{
   const p=await project(client,a.projectID);await this.batch(client,p,a.batchID!);
   const job=await this.job(client,p,a.batchID!,a.jobID!,true);
   const kind=input.logType??(input.fileName.endsWith('.resim.jsonl')?'EMISSIONS_LOG':'OTHER_LOG'),mime=mediaType(input.fileName,kind);
   const prior=await client.query('SELECT * FROM api.uploads WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 AND file_name=$5',
    [p.tenant_id,p.id,a.batchID,a.jobID,input.fileName]);
   if(prior.rows.length){
    const row=prior.rows[0];if(row.checksum!==input.checksum||Number(row.size_bytes)!==input.fileSize||row.log_type!==kind||row.media_type!==mime)
     throw new ApiError(409,'log name already has another registered identity');
    if(job.close_status!==null&&(job.closed_at||row.version_id!==null||row.retained_at!==null))
     throw new ApiError(400,'bound or closed upload cannot be renewed');
    return row as Upload;
   }
   if(job.close_status!==null)throw new ApiError(400,'job is closing or closed');
   const count=await client.query('SELECT count(*)::int AS total FROM api.uploads WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4',[p.tenant_id,p.id,a.batchID,a.jobID]);
   if(count.rows[0].total>=this.maximumUploads)throw new ApiError(400,'registered upload count exceeds this recipe');
   const id=randomUUID(),key=[p.tenant_id,p.id,a.batchID!,a.jobID!,id,'payload'].join('/');
   const found=await client.query('INSERT INTO api.uploads(tenant_id,project_id,batch_id,job_id,id,file_name,checksum,size_bytes,media_type,log_type,object_key) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING *',
    [p.tenant_id,p.id,a.batchID,a.jobID,id,input.fileName,input.checksum,input.fileSize,mime,kind,key]);
   return found.rows[0] as Upload;
  });
  return this.storage.presign(upload);
 }
 async closeJob(principal:Principal,a:Addresses,input:{status:'SUCCEEDED'|'ERROR';errorMessage?:string},signal:AbortSignal){
  if(input.status!=='ERROR'&&input.errorMessage!==undefined)throw new ApiError(400,'errorMessage requires ERROR status');
  const ids=await transaction(this.pool,principal,async client=>{
   const p=await project(client,a.projectID);await this.batch(client,p,a.batchID!);
   const job=await this.job(client,p,a.batchID!,a.jobID!,true);
   if(job.close_status!==null&&(job.close_status!==input.status||job.close_error!==(input.errorMessage??null)))
    throw new ApiError(409,'job already has another close claim');
   if(job.close_status===null)await client.query('UPDATE api.jobs SET close_status=$5,close_error=$6 WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND id=$4',
    [p.tenant_id,p.id,a.batchID,a.jobID,input.status,input.errorMessage??null]);
   const uploads=await client.query('SELECT id FROM api.uploads WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 ORDER BY id',
    [p.tenant_id,p.id,a.batchID,a.jobID]);
   return job.closed_at?[]:uploads.rows.map(row=>String(row.id));
  });
  for(const id of ids){
   signal.throwIfAborted();
   // PostgreSQL owns a session advisory lock; no SQL transaction spans the finite worker.
   const lock=await this.pool.connect();let acquired=false;
   try{
    const observed=await lock.query('SELECT pg_try_advisory_lock(hashtextextended($1,0)) AS acquired',[id]);
    acquired=observed.rows[0].acquired;if(!acquired)throw new ApiError(503,'custody is active; retry the same close');
    let upload=await transactionClient(lock,principal,async client=>{
     const p=await project(client,a.projectID);await this.job(client,p,a.batchID!,a.jobID!);
     const rows=await client.query('SELECT * FROM api.uploads WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 AND id=$5',
      [p.tenant_id,p.id,a.batchID,a.jobID,id]);
     if(rows.rows.length!==1)throw new ApiError(404,'upload not found');
     return rows.rows[0] as Upload&{retained_at:Date|null};
    });
    if(upload.retained_at)continue;
    if(upload.version_id===null){
     const version=await this.storage.version(upload,signal);
     upload=await transactionClient(lock,principal,async client=>{
      const p=await project(client,a.projectID);
      const rows=await client.query('UPDATE api.uploads SET version_id=$6 WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 AND id=$5 AND version_id IS NULL RETURNING *',
       [p.tenant_id,p.id,a.batchID,a.jobID,id,version]);
      if(rows.rows.length!==1)throw new ApiError(409,'upload version binding changed');
      return rows.rows[0] as Upload&{retained_at:Date|null};
     });
    }
    const proofs=await this.retention.retain(upload,signal);
    await transactionClient(lock,principal,async client=>{
     const p=await project(client,a.projectID);
     const rows=await client.query('SELECT version_id,retained_at FROM api.uploads WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 AND id=$5 FOR UPDATE',
      [p.tenant_id,p.id,a.batchID,a.jobID,id]);
     if(rows.rows.length!==1||rows.rows[0].version_id!==upload.version_id||rows.rows[0].retained_at)
      throw new ApiError(409,'upload custody checkpoint changed');
     for(const proof of proofs)await client.query('INSERT INTO api.upload_proofs(tenant_id,project_id,batch_id,job_id,upload_id,role,raw,sha256) VALUES($1,$2,$3,$4,$5,$6,$7,$8)',
      [p.tenant_id,p.id,a.batchID,a.jobID,id,proof.role,proof.raw,proof.sha256]);
     await client.query('UPDATE api.uploads SET retained_at=now() WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 AND id=$5',
      [p.tenant_id,p.id,a.batchID,a.jobID,id]);
    });
   }finally{
    let healthy=false;
    try{if(acquired)await lock.query('SELECT pg_advisory_unlock(hashtextextended($1,0))',[id]);healthy=true}
    finally{lock.release(!healthy)}
   }
  }
  await transaction(this.pool,principal,async client=>{
   const p=await project(client,a.projectID),job=await this.job(client,p,a.batchID!,a.jobID!,true);
   if(job.closed_at)return;
   const remaining=await client.query('SELECT id FROM api.uploads WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND job_id=$4 AND retained_at IS NULL',
    [p.tenant_id,p.id,a.batchID,a.jobID]);
   if(remaining.rows.length)throw new ApiError(503,'custody remains incomplete; retry the same close');
   await client.query('UPDATE api.jobs SET closed_at=now() WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND id=$4',
    [p.tenant_id,p.id,a.batchID,a.jobID]);
  });
 }
 closeBatch(principal:Principal,a:Addresses){
  return transaction(this.pool,principal,async client=>{
   const p=await project(client,a.projectID),batch=await this.batch(client,p,a.batchID!,true);
   if(batch.closed_at)return;
   const incomplete=await client.query('SELECT id FROM api.jobs WHERE tenant_id=$1 AND project_id=$2 AND batch_id=$3 AND closed_at IS NULL',[p.tenant_id,p.id,a.batchID]);
   if(incomplete.rows.length)throw new ApiError(409,'batch contains open jobs');
   await client.query('UPDATE api.batches SET closed_at=now() WHERE tenant_id=$1 AND project_id=$2 AND id=$3',[p.tenant_id,p.id,a.batchID]);
  });
 }
}
