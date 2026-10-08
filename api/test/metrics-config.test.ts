import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {generateKeyPair,exportJWK,SignJWT} from 'jose';
import {createApi} from '../src/app.js';
import type {Domain} from '../src/domain.js';
import {metricsConfigBytes,CONFIG_MAX_BYTES,TEMPLATE_MAX_BYTES,CONFIG_TOTAL_MAX_BYTES} from '../src/metrics-config.js';
const b64=(value:string|Buffer)=>Buffer.from(value).toString('base64');
const input={projectId:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',branch:'main',config:b64('version: 1\n'),templateFiles:[]};
test('opaque bytes and canonical identity preserve Liquid and reject permissive base64',()=>{
 const raw=Buffer.from([0,255,128,10]),template=Buffer.from('{% include "/etc/passwd" %} {{ secret | eval }}');
 const observed=metricsConfigBytes({...input,config:b64(raw),templateFiles:[{name:'probe.LIQUID',contents:b64(template)}]});
 assert.deepEqual(observed.config,raw);assert.deepEqual(Buffer.from(observed.templates[0].contents,'base64'),template);
 for(const config of ['YQ','YQ===','YR==','YQ==\n','-_=='])assert.throws(()=>metricsConfigBytes({...input,config}),/base64/);
 assert.equal(metricsConfigBytes({...input,templateFiles:[{name:'b.liquid',contents:b64('b')},{name:'a.liquid',contents:b64('a')}]}).snapshotSha256,
  metricsConfigBytes({...input,templateFiles:[{name:'a.liquid',contents:b64('a')},{name:'b.liquid',contents:b64('b')}]}).snapshotSha256);
});
test('finite decoded bounds and basename/count admission refuse before storage',()=>{
 assert.equal(metricsConfigBytes({...input,config:b64(Buffer.alloc(CONFIG_MAX_BYTES))}).config.length,CONFIG_MAX_BYTES);
 assert.throws(()=>metricsConfigBytes({...input,config:b64(Buffer.alloc(CONFIG_MAX_BYTES+1))}),/base64/);
 for(const name of ['../a.liquid','a\\b.liquid','a\u0000.liquid','a.txt'])assert.throws(()=>metricsConfigBytes({...input,templateFiles:[{name,contents:''}]}),/basename/);
 assert.throws(()=>metricsConfigBytes({...input,templateFiles:[{name:'a.liquid',contents:''},{name:'a.liquid',contents:''}]}),/duplicate/);
 assert.throws(()=>metricsConfigBytes({...input,templateFiles:Array.from({length:33},(_,i)=>({name:i+'.liquid',contents:''}))}),/count/);
 assert.throws(()=>metricsConfigBytes({...input,templateFiles:[{name:'a.liquid',contents:b64(Buffer.alloc(TEMPLATE_MAX_BYTES+1))}]}),/base64/);
 assert.throws(()=>metricsConfigBytes({...input,config:b64(Buffer.alloc(CONFIG_MAX_BYTES)),templateFiles:Array.from({length:5},(_,i)=>({name:i+'.liquid',contents:b64(Buffer.alloc(TEMPLATE_MAX_BYTES))}))}),/combined/);
 assert.equal(CONFIG_TOTAL_MAX_BYTES,2*CONFIG_MAX_BYTES);
});
test('real JWT/JWKS Fastify GraphQL engine: SDK variables, selection, errors, bounded pre-effect parsing',async()=>{
 const {privateKey,publicKey}=await generateKeyPair('RS256');const jwk=await exportJWK(publicKey);jwk.kid='fixture';
 const server=createServer((_request,response)=>{response.setHeader('content-type','application/json');response.end(JSON.stringify({keys:[jwk]}))});
 await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));const address=server.address();assert.ok(address&&typeof address!=='string');
 const issuer='https://fixture.invalid',token=await new SignJWT({resource_access:{'sdk-api':{roles:['sdk-write']}}}).setProtectedHeader({alg:'RS256',typ:'JWT',kid:'fixture'}).setIssuer(issuer).setAudience('sdk-api').setSubject('subject-a').setExpirationTime('2m').sign(privateKey);
 let domainCalls=0;const principals:string[]=[],signals:AbortSignal[]=[];
 const domain={storage:{maximumBytes:1},async updateMetricsConfig(principal:{subject:string},value:typeof input,signal:AbortSignal){domainCalls++;principals.push(principal.subject);signals.push(signal);metricsConfigBytes(value)}} as unknown as Domain;
 const api=createApi(domain,{issuer,audience:'sdk-api',jwksUrl:'http://127.0.0.1:'+address.port,requiredRole:'sdk-write'});
 const document='mutation UpdateMetricsConfig($projectId:String!,$config:String!,$templateFiles:[MetricsTemplate!]!,$branch:String){updateMetricsConfig(projectId:$projectId,config:$config,templateFiles:$templateFiles,branch:$branch)}';
 const post=(payload:unknown)=>api.inject({method:'POST',url:'/graphql',headers:{authorization:'Bearer '+token,'content-type':'application/json'},payload:JSON.stringify(payload)});
 try{
  const response=await post({query:document,operationName:'UpdateMetricsConfig',variables:input});assert.equal(response.statusCode,200);assert.deepEqual(response.json(),{data:{updateMetricsConfig:true}});assert.equal(domainCalls,1);assert.deepEqual(principals,['subject-a']);assert.ok(signals[0] instanceof AbortSignal);
  const alias=await post({query:'mutation First { alias:updateMetricsConfig(projectId:"'+input.projectId+'",config:"",templateFiles:[],branch:"main") } mutation Other { _missing }',operationName:'First'});
  // GraphQL validates the complete document, including an unselected invalid operation.
  assert.ok(alias.json().errors);assert.equal(domainCalls,1);
  const selected=await post({query:'mutation First { alias:updateMetricsConfig(projectId:"'+input.projectId+'",config:"",templateFiles:[],branch:"main") } query Other { _empty }',operationName:'First'});assert.deepEqual(selected.json(),{data:{alias:true}});assert.equal(domainCalls,2);
  for(const payload of [{query:document,variables:{...input,projectId:7}},{query:'mutation { unknown }'},[{query:document,variables:input}],{query:'{ __schema { types { name } } }'},{query:'query { '+Array.from({length:65},(_,i)=>'a'+i+':_empty').join(' ')+' }'},{query:'query { '+Array.from({length:2200},()=> '_empty').join(' ')+' }'}]){
   const refusal=await post(payload);assert.ok(refusal.statusCode>=400||refusal.json().errors);assert.equal(domainCalls,2);
  }
  const malformed=await post({query:document,variables:{...input,config:'SENSITIVE_CONFIG_MARKER'}});assert.ok(malformed.json().errors);assert.equal(domainCalls,3);assert.ok(!malformed.body.includes('SENSITIVE_CONFIG_MARKER'));
  const unauthorized=await api.inject({method:'POST',url:'/graphql',payload:{query:document,variables:input}});assert.equal(unauthorized.statusCode,401);assert.equal(domainCalls,3);
  assert.equal((await api.inject({method:'GET',url:'/graphiql',headers:{authorization:'Bearer '+token}})).statusCode,404);
 }finally{await api.close();await new Promise<void>((resolve,reject)=>server.close(error=>error?reject(error):resolve()))}
});
