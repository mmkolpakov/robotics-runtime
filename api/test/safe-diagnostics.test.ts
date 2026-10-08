import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {retainDiagnostic,publishSafeFiles,redactDiagnostics} from './safe-diagnostics.mjs';

test('real fixture diagnostic capture strips HTTP failure authority before retained closure',async()=>{
 const work=await mkdtemp(join(tmpdir(),'api-diagnostic-'));
 const marker='synthetic-private-authority-marker';
 const original='httpx.HTTPStatusError: 403 Forbidden for url http://user:password@s3-fixture:8333/bucket/payload?X-Amz-Credential='+marker+'&X-Amz-Signature=secret-signature\nAuthorization: Bearer '+marker+'\nclient_secret='+marker+'\n';
 try{
  await retainDiagnostic(work,'consumer-failure.log',original,[marker]);
  const safe=await readFile(join(work,'consumer-failure.log'),'utf8');
  assert.match(safe,/httpx.HTTPStatusError: 403 Forbidden/);
  assert.match(safe,/s3-fixture:8333\/bucket\/payload/);
  for(const value of [marker,'secret-signature','user:password','X-Amz-Credential'])assert.ok(!safe.includes(value));
  await writeFile(join(work,'payload'),'opaque external payload\n');
  await publishSafeFiles(work,join(work,'public'),['consumer-failure.log','payload'],[marker]);
  const manifest=JSON.parse(await readFile(join(work,'public/safe-manifest.json'),'utf8'));assert.equal(manifest.length,2);
  await writeFile(join(work,'raw-failure.log'),original);
  await assert.rejects(publishSafeFiles(work,join(work,'refused'),['payload','raw-failure.log'],[marker]),/authority/);
  await assert.rejects(readFile(join(work,'refused/payload')),/ENOENT/);
 }finally{await rm(work,{recursive:true,force:true})}
});

test('double sanitization retains structured worker JSON and escaped URL diagnostics',()=>{
 const marker='synthetic-double-pass-authority';
 const original=JSON.stringify({kind:'custody-operation-refused',uploadId:'fixed-upload',operation:'download',exitCode:255,
  stderr:'Could not connect to endpoint URL: "http://s3-fixture:8333/bucket/payload?X-Amz-Signature='+marker+'"\n'});
 const first=redactDiagnostics(original,[marker]);
 const second=redactDiagnostics(first,[marker]);
 const value=JSON.parse(second);
 assert.equal(value.operation,'download');assert.equal(value.exitCode,255);
 assert.match(value.stderr,/Could not connect/);assert.match(value.stderr,/s3-fixture:8333\/bucket\/payload/);
 assert.ok(!second.includes(marker)&&!second.includes('X-Amz-Signature'));
});
