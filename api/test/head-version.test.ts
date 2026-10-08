import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createHash} from 'node:crypto';
import {UploadStorage} from '../src/uploads.js';
test('a wire HEAD cannot substitute another version with identical content facts',async()=>{
 const checksum=createHash('sha256').update(Buffer.alloc(0)).digest('hex');
 const requested:string[]=[];
 const server=createServer((request,response)=>{
  const url=new URL(request.url!,'http://fixture');requested.push(url.searchParams.get('versionId')!);
  response.writeHead(200,{'content-length':'0','content-type':'text/plain','x-amz-version-id':'v2',
   'x-amz-checksum-sha256':Buffer.from(checksum,'hex').toString('base64'),
   'x-amz-meta-upload-id':'upload-fixture','x-amz-meta-run-id':'run-00000000-0000-4000-8000-000000000001',
   'x-amz-meta-sha256':checksum});response.end();
 });
 await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
 const address=server.address();assert.ok(address&&typeof address==='object');
 const prior={access:process.env.AWS_ACCESS_KEY_ID,secret:process.env.AWS_SECRET_ACCESS_KEY};
 process.env.AWS_ACCESS_KEY_ID='public-wire-fixture';process.env.AWS_SECRET_ACCESS_KEY='public-wire-fixture';
 const storage=new UploadStorage('fixture-evidence','http://127.0.0.1:'+address.port,'us-east-1',1024);
 try{
  await assert.rejects(storage.version({id:'upload-fixture',job_id:'00000000-0000-4000-8000-000000000001',
   object_key:'payload',checksum,size_bytes:'0',media_type:'text/plain',version_id:'v1'},AbortSignal.timeout(5000)),
   error=>error instanceof Error&&error.message==='uploaded object does not match its registered identity');
  assert.deepEqual(requested,['v1']);
 }finally{
  storage.close();if(prior.access===undefined)delete process.env.AWS_ACCESS_KEY_ID;else process.env.AWS_ACCESS_KEY_ID=prior.access;
  if(prior.secret===undefined)delete process.env.AWS_SECRET_ACCESS_KEY;else process.env.AWS_SECRET_ACCESS_KEY=prior.secret;
  await new Promise<void>(resolve=>server.close(()=>resolve()));
 }
});
