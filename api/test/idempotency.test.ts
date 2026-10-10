import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {generateKeyPair,exportJWK,SignJWT} from 'jose';
import {creationKey,creationFingerprint} from '../src/idempotency.js';
import {createApi} from '../src/app.js';
import type {Domain} from '../src/domain.js';
test('Structured Fields string parsing rejects ambiguous keys before effects',()=>{
 assert.equal(creationKey(undefined),undefined);
 assert.equal(creationKey(' "one" '),'one');
 assert.equal(creationKey('"\\\"one\\\""'),'"one"');
 assert.equal(creationKey('"'+ 'x'.repeat(256)+'"'),'x'.repeat(256));
 for(const value of ['', 'one', '1', '?1', ':YWJj:', '""', '"one";scope=1', '"one", "two"', '"one" trailing', '"'+ 'x'.repeat(257)+'"', ' '.repeat(1025), ['"one"','"two"']]){
  assert.throws(()=>creationKey(value),/Idempotency-Key/);
 }
 assert.equal(creationFingerprint(['branch',null,null]),creationFingerprint(['branch',null,null]));
 assert.notEqual(creationFingerprint(['branch','name',null]),creationFingerprint(['branch',null,'name']));
});
test('authenticated creation routes pass only parsed keys; unkeyed callers remain supported',async()=>{
 const {privateKey,publicKey}=await generateKeyPair('RS256');const jwk=await exportJWK(publicKey);jwk.kid='fixture';
 const server=createServer((_request,response)=>{response.setHeader('content-type','application/json');response.end(JSON.stringify({keys:[jwk]}))});
 await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));const address=server.address();assert.ok(address&&typeof address!=='string');
 const issuer='https://fixture.invalid',token=await new SignJWT({resource_access:{'sdk-api':{roles:['sdk-write']}}}).setProtectedHeader({alg:'RS256',typ:'JWT',kid:'fixture'}).setIssuer(issuer).setAudience('sdk-api').setSubject('subject-a').setExpirationTime('2m').sign(privateKey);
 const calls:unknown[][]=[];
 const domain={storage:{maximumBytes:1},async createBatch(...args:unknown[]){calls.push(args);return {batchID:'created'}},async createJob(...args:unknown[]){calls.push(args);return {jobID:'created'}}} as unknown as Domain;
 const api=createApi(domain,{issuer,audience:'sdk-api',jwksUrl:'http://127.0.0.1:'+address.port,requiredRole:'sdk-write'});
 const project='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',batch='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
 const options={method:'POST' as const,headers:{authorization:'Bearer '+token,'idempotency-key':'"same-key"'}};
 try{
  assert.equal((await api.inject({...options,url:'/projects/'+project+'/batches/light',payload:{branchID:batch}})).statusCode,201);
  assert.equal((await api.inject({...options,url:'/projects/'+project+'/batches/'+batch+'/jobs',payload:{name:'probe'}})).statusCode,201);
  assert.equal(calls.length,2);assert.equal(calls[0][3],'same-key');assert.equal(calls[1][3],'same-key');
  for(const header of ['raw-key','""','"first", "second"','"key";param','"'+ 'x'.repeat(257)+'"']){
   const refused=await api.inject({...options,headers:{...options.headers,'idempotency-key':header},url:'/projects/'+project+'/batches/light',payload:{branchID:batch}});
   assert.equal(refused.statusCode,400);assert.equal(calls.length,2);
  }
  const unkeyed=await api.inject({...options,headers:{authorization:'Bearer '+token},url:'/projects/'+project+'/batches/light',payload:{branchID:batch}});
  assert.equal(unkeyed.statusCode,201);assert.equal(calls.length,3);assert.equal(calls[2][3],undefined);
 }finally{await api.close();await new Promise<void>((resolve,reject)=>server.close(error=>error?reject(error):resolve()))}
});
