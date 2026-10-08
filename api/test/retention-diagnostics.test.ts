import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {Retention} from '../src/retention.js';
import type {Jobs,JobResult,JobRequest} from '@robotics-runtime/host';
import type {Upload} from '../src/uploads.js';

for(const [index,operation]of ['download','predicate','sign','verify','receipt'].entries()){
 test('settled '+operation+' refusal retains safe correlated original worker result',async()=>{
  const root=await mkdtemp(join(tmpdir(),'api-operation-')),records:string[]=[],requests:JobRequest[]=[];
  const marker='synthetic-operation-private-marker';
  const failure:JobResult={ok:false,exitCode:73,signal:undefined,timedOut:false,canceled:false,code:'FIXTURE_REFUSAL',durationMs:19,
   diagnostic:'Command failed: aws --bucket secret-argv-marker env=secret-env-marker',stdout:'private '+marker,
   stderr:'HTTPStatusError 403 for http://s3-fixture/payload?X-Amz-Credential='+marker+'\nBearer '+marker};
  const original=console.error;
  const jobs={run:async(request:JobRequest)=>{requests.push(request);return requests.length===index+1?failure:
   {ok:true,exitCode:0,signal:undefined,timedOut:false,canceled:false,code:undefined,durationMs:1,diagnostic:undefined,stdout:'{}',stderr:''}}} as unknown as Jobs;
  const upload={id:'11111111-1111-4111-8111-111111111111',job_id:'22222222-2222-4222-8222-222222222222',
   version_id:'immutable-v1',size_bytes:'0',checksum:'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
   media_type:'text/plain',object_key:'server/owned/payload'} as Upload;
  try{
   console.error=(value:unknown)=>{records.push(String(value))};
   const retention=new Retention(jobs,{root,bucket:'fixed-bucket',maximumBytes:8388608,environment:{COSIGN_PASSWORD:marker},
    keyPath:'/fixed/key',publicKeyPath:'/fixed/public',signingConfiguration:'/fixed/signing',trustedRoot:'/fixed/root'});
   await assert.rejects(retention.retain(upload,AbortSignal.timeout(1000)),error=>error instanceof Error&&error.cause===failure);
   assert.equal(requests.length,index+1);assert.equal(records.length,1);
   const record=JSON.parse(records[0]);assert.equal(record.uploadId,upload.id);assert.equal(record.operation,operation);
   assert.equal(record.exitCode,73);assert.equal(record.code,'FIXTURE_REFUSAL');assert.equal(record.durationMs,19);
   assert.equal(record.timedOut,false);assert.equal(record.canceled,false);assert.equal(record.signal,null);
   assert.match(record.stderr,/HTTPStatusError 403/);assert.ok(!records[0].includes(marker));assert.ok(!records[0].includes('X-Amz-Credential'));
   assert.ok(!('args'in record)&&!('env'in record)&&!('diagnostic'in record));
   assert.ok(!records[0].includes('secret-argv-marker')&&!records[0].includes('secret-env-marker'));
   assert.equal(requests.at(-1)?.extendEnv,false);assert.equal(requests.at(-1)?.timeoutMs,45000);
   assert.deepEqual(await readdir(root),[]);
  }finally{console.error=original;await rm(root,{recursive:true,force:true})}
 });
}

test('thrown worker cause is rethrown without command or environment diagnostic',async()=>{
 const root=await mkdtemp(join(tmpdir(),'api-thrown-')),records:string[]=[];
 const failure=Object.assign(new Error('Command argv-marker env-marker'),{code:'ENOENT'});
 const original=console.error;
 try{
  console.error=(value:unknown)=>{records.push(String(value))};
  const jobs={run:async()=>{throw failure}} as unknown as Jobs;
  const retention=new Retention(jobs,{root,bucket:'fixed',maximumBytes:1024,environment:{},
   keyPath:'/fixed/key',publicKeyPath:'/fixed/public',signingConfiguration:'/fixed/signing',trustedRoot:'/fixed/root'});
  const upload={id:'11111111-1111-4111-8111-111111111111',job_id:'22222222-2222-4222-8222-222222222222',
   version_id:'v1',size_bytes:'0',checksum:'0'.repeat(64),media_type:'text/plain',object_key:'fixed/payload'} as Upload;
  await assert.rejects(retention.retain(upload,AbortSignal.timeout(1000)),error=>error===failure);
  const record=JSON.parse(records[0]);assert.equal(record.operation,'download');assert.equal(record.thrownName,'Error');assert.equal(record.thrownCode,'ENOENT');
  assert.ok(!records[0].includes('argv-marker')&&!records[0].includes('env-marker'));
 }finally{console.error=original;await rm(root,{recursive:true,force:true})}
});
