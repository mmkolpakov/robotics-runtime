import assert from 'node:assert/strict';
import {retainDiagnostic,assertSafeArtifact,redactDiagnostics} from './safe-diagnostics.mjs';
import {request as wireRequest} from 'node:http';
import {randomUUID,randomBytes,createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {Pool} from 'pg';
import {S3Client,CreateBucketCommand,PutBucketVersioningCommand,HeadObjectCommand,GetObjectCommand,ListBucketsCommand} from '@aws-sdk/client-s3';
const root=resolve(new URL('../../',import.meta.url).pathname),lock=JSON.parse(await readFile(join(root,'api/test/upstream-lock.json'),'utf8'));
const owner='rr-sdk-api-'+randomUUID().slice(0,8),network=owner+'-net',bootstrap=owner+'-bootstrap',names=[],volumes=[],networks=[];
const engine=process.env.API_FIXTURE_ENGINE??'podman',suite=process.env.API_FIXTURE_SUITE??owner;
assert.ok(['podman','docker'].includes(engine));assert.match(suite,/^[a-z0-9-]{1,80}$/);
const apiImage=process.env.API_FIXTURE_IMAGE,sdkImage=process.env.API_FIXTURE_SDK_IMAGE;
assert.ok(apiImage&&sdkImage,'explicit built API and SDK fixture images required');
const secrets=join(root,'artifacts',owner,'secrets'),output=join(root,'artifacts',owner);
await mkdir(secrets,{recursive:true,mode:0o700});
await writeFile(join(output,'fixture-owner.json'),JSON.stringify({owner,suite})+'\n');
const password=randomBytes(24).toString('hex'),kcPassword=randomBytes(24).toString('hex'),apiPassword=randomBytes(24).toString('hex');
const access=randomBytes(12).toString('hex'),secret=randomBytes(24).toString('hex'),signingPassword=randomBytes(24).toString('hex');
const privateValues=[password,kcPassword,apiPassword,access,secret,signingPassword];
const env={...process.env,POSTGRES_PASSWORD:password,KC_DB_PASSWORD:kcPassword,KC_BOOTSTRAP_ADMIN_PASSWORD:kcPassword,AWS_ACCESS_KEY_ID:access,AWS_SECRET_ACCESS_KEY:secret,COSIGN_PASSWORD:signingPassword};
const report={engine,scope:'Installed SDK1.8.0 external Test, local Keycloak/PG18.6/SeaweedFS4.29 only',owner,steps:[]};
function cmd(args){const p=spawnSync(engine,args,{env,encoding:'utf8',timeout:120000});if(p.status!==0)throw new Error(args[0]+' failed: '+p.stderr);return p.stdout.trim()}
function logs(name){const p=spawnSync(engine,['logs',name],{env,encoding:'utf8',timeout:30000});if(p.status!==0)throw new Error('container logs unavailable');return p.stdout+p.stderr}
function volume(suffix){const name=owner+'-'+suffix;cmd(['volume','create','--label','org.robotics.runtime.fixture-owner='+owner,'--label','org.robotics.runtime.fixture-suite='+suite,name]);volumes.push(name);return name}
function launch(suffix,image,args,extra=[]){const name=owner+'-'+suffix;cmd(['run','--detach','--name',name,'--label','org.robotics.runtime.fixture-owner='+owner,'--label','org.robotics.runtime.fixture-suite='+suite,'--log-driver',engine==='docker'?'local':'k8s-file','--network',network,'--network-alias',suffix,...extra,image,...args]);names.push(name);if(['pg','keycloak','s3-fixture','api'].includes(suffix))cmd(['network','connect','--alias',suffix,bootstrap,name]);return name}
function port(name,p){return Number(cmd(['port',name,p+'/tcp']).split(':').at(-1))}
async function eventually(work){let last;for(let i=0;i<120;i++){try{return await work()}catch(e){last=e;await new Promise(r=>setTimeout(r,250))}}throw last}
async function http(url,options={}){const response=await fetch(url,{...options,signal:options.signal??AbortSignal.timeout(10000)});if(!response.ok)throw new Error('HTTP bootstrap refused '+response.status);if(response.status===204||response.headers.get('content-length')==='0')return null;const raw=await response.text();return raw?JSON.parse(raw):null}
let pgAdmin,apiAdmin,s3,seaweed;
try{
 for(const [name,internal]of [[network,true],[bootstrap,false]]){
  cmd(['network','create',...(internal?['--internal']:[]),'--label','org.robotics.runtime.fixture-owner='+owner,'--label','org.robotics.runtime.fixture-suite='+suite,name]);
  const item={name,id:null,internal};networks.push(item);
  const d=JSON.parse(cmd(['network','inspect',name]))[0],labels=d.Labels??d.labels;
  assert.equal(labels['org.robotics.runtime.fixture-owner'],owner);assert.equal(labels['org.robotics.runtime.fixture-suite'],suite);
  assert.equal(d.Internal??d.internal,internal);item.id=d.Id??d.id;assert.match(item.id,/^[0-9a-f]{64}$/);
 }

 const pgVolume=volume('pg'),s3Volume=volume('s3'),secretVolume=volume('secrets'),workVolume=volume('work');
 const pg=launch('pg',lock.postgres,[],['--memory','384m','-e','POSTGRES_PASSWORD','-p','127.0.0.1::5432','--mount','type=volume,source='+pgVolume+',target=/var/lib/postgresql']);
 const pgPort=port(pg,5432);
 pgAdmin=new Pool({host:'127.0.0.1',port:pgPort,user:'postgres',password,database:'postgres',connectionTimeoutMillis:1000});
 await eventually(()=>pgAdmin.query('SELECT 1'));
 for(const sql of ['CREATE ROLE api_owner NOLOGIN',"CREATE ROLE api_app LOGIN PASSWORD '"+apiPassword+"'","CREATE ROLE keycloak_user LOGIN PASSWORD '"+kcPassword+"'",'CREATE DATABASE api OWNER api_owner','CREATE DATABASE identity OWNER keycloak_user'])await pgAdmin.query(sql);
 apiAdmin=new Pool({host:'127.0.0.1',port:pgPort,user:'postgres',password,database:'api'});
 await apiAdmin.query(await readFile(join(root,'api/sql/001-external-tests.sql'),'utf8'));
 const kc=launch('keycloak',lock.keycloak,['start-dev','--http-port=8080'],['--memory','768m','-e','KC_DB=postgres','-e','KC_DB_URL=jdbc:postgresql://pg:5432/identity','-e','KC_DB_USERNAME=keycloak_user','-e','KC_DB_PASSWORD','-e','KC_BOOTSTRAP_ADMIN_USERNAME=fixture-admin','-e','KC_BOOTSTRAP_ADMIN_PASSWORD','-e','KC_HOSTNAME=http://keycloak:8080','-p','127.0.0.1::8080']);
 const kcUrl='http://127.0.0.1:'+port(kc,8080);
 await eventually(()=>http(kcUrl+'/realms/master/.well-known/openid-configuration'));
 const admin=await http(kcUrl+'/realms/master/protocol/openid-connect/token',{method:'POST',body:new URLSearchParams({grant_type:'password',client_id:'admin-cli',username:'fixture-admin',password:kcPassword})});
 privateValues.push(admin.access_token);
 const auth={Authorization:'Bearer '+admin.access_token,'Content-Type':'application/json'},adminApi=path=>kcUrl+'/admin/realms/'+path;
 await http(adminApi(''),{method:'POST',headers:auth,body:JSON.stringify({realm:'sdk',enabled:true})});
 async function createClient(value){await http(adminApi('sdk/clients'),{method:'POST',headers:auth,body:JSON.stringify(value)});const list=await http(adminApi('sdk/clients?clientId='+value.clientId),{headers:auth});assert.equal(list.length,1);return list[0]}
 const apiClient=await createClient({clientId:'sdk-api',enabled:true,bearerOnly:true});
 await http(adminApi('sdk/clients/'+apiClient.id+'/roles'),{method:'POST',headers:auth,body:JSON.stringify({name:'sdk-write'})});
 const role=await http(adminApi('sdk/clients/'+apiClient.id+'/roles/sdk-write'),{headers:auth}),tenants=[];
 for(const label of ['a','b']){
  const clientSecret=randomBytes(24).toString('hex');
  const client=await createClient({clientId:'tenant-'+label,enabled:true,publicClient:false,serviceAccountsEnabled:true,standardFlowEnabled:false,secret:clientSecret,protocolMappers:[{name:'api-audience',protocol:'openid-connect',protocolMapper:'oidc-audience-mapper',config:{'included.client.audience':'sdk-api','access.token.claim':'true','id.token.claim':'false'}}]});
  const account=await http(adminApi('sdk/clients/'+client.id+'/service-account-user'),{headers:auth});
  await http(adminApi('sdk/users/'+account.id+'/role-mappings/clients/'+apiClient.id),{method:'POST',headers:auth,body:JSON.stringify([role])});
  const token=await http(kcUrl+'/realms/sdk/protocol/openid-connect/token',{method:'POST',body:new URLSearchParams({grant_type:'client_credentials',client_id:client.clientId,client_secret:clientSecret})});
  privateValues.push(clientSecret,token.access_token);
  const tenant=randomUUID(),project=randomUUID(),branch=randomUUID(),principal=randomUUID();
  await apiAdmin.query('INSERT INTO api.tenants VALUES($1)',[tenant]);
  await apiAdmin.query('INSERT INTO api.memberships VALUES($1,$2,$3,$4,$5)',[tenant,'http://keycloak:8080/realms/sdk',account.id,account.username,principal]);
  await apiAdmin.query('INSERT INTO api.projects VALUES($1,$2,$3)',[tenant,project,'Project '+label]);
  await apiAdmin.query('INSERT INTO api.project_memberships VALUES($1,$2,$3,$4)',[tenant,project,'http://keycloak:8080/realms/sdk',account.id]);
  await apiAdmin.query("INSERT INTO api.branches(tenant_id,project_id,id,name,branch_type,created_by) VALUES($1,$2,$3,'main','MAIN',$4)",[tenant,project,branch,principal]);
  tenants.push({tenant,project,branch,subject:account.id,token:token.access_token,clientId:client.clientId,clientSecret,accountId:account.id});
 }
 report.steps.push({name:'actual-Keycloak-two-service-account-JWT-and-PG-membership',tenants:2});
 seaweed=launch('s3-fixture',lock.s3,['server','-s3','-dir=/data','-s3.port=8333','-s3.ip.bind=0.0.0.0','-volume.max=2','-master.volumeSizeLimitMB=64'],['--memory','512m','-e','AWS_ACCESS_KEY_ID','-e','AWS_SECRET_ACCESS_KEY','-p','127.0.0.1::8333','--mount','type=volume,source='+s3Volume+',target=/data']);
 s3=new S3Client({endpoint:'http://127.0.0.1:'+port(seaweed,8333),region:'us-east-1',forcePathStyle:true,credentials:{accessKeyId:access,secretAccessKey:secret},requestChecksumCalculation:'WHEN_REQUIRED'});
 const bucket='sdk-api-evidence';
 async function bootstrapS3(operation,work){
  report.bootstrapS3={operation,status:'pending'};
  try{const value=await work();report.bootstrapS3={operation,status:'passed'};return value}
  catch(error){
   report.bootstrapS3={operation,status:'refused',errorName:error.name,errorCode:error.code??null,
    statusCode:error.$metadata?.httpStatusCode??null,attempts:error.$metadata?.attempts??null};
   const d=JSON.parse(cmd(['inspect',seaweed]))[0];
   report.s3Failure={state:{running:d.State.Running,exitCode:d.State.ExitCode,oomKilled:d.State.OOMKilled,error:d.State.Error},
    networks:Object.fromEntries(Object.entries(d.NetworkSettings.Networks).map(([name,n])=>[name,{ipAddress:n.IPAddress,aliases:n.Aliases}])),bindings:d.NetworkSettings.Ports};
   await retainDiagnostic(output,'s3-failure.log',logs(seaweed),privateValues);
   throw error;
  }
 }
 await bootstrapS3('ListBuckets-ready',()=>eventually(()=>s3.send(new ListBucketsCommand({}),{abortSignal:AbortSignal.timeout(10000)})));
 await bootstrapS3('CreateBucket',()=>s3.send(new CreateBucketCommand({Bucket:bucket}),{abortSignal:AbortSignal.timeout(10000)}));
 await bootstrapS3('PutBucketVersioning',()=>s3.send(new PutBucketVersioningCommand({Bucket:bucket,VersioningConfiguration:{Status:'Enabled'}}),{abortSignal:AbortSignal.timeout(10000)}));
 report.steps.push({name:'authenticated-S3-ready-create-and-versioning',readyOperation:'ListBuckets'});

 const material={'api-database-url':'postgresql://api_app:'+apiPassword+'@pg:5432/api','s3-credentials':'[default]\naws_access_key_id='+access+'\naws_secret_access_key='+secret+'\n','s3-config':'[default]\nregion=us-east-1\n','custody-password':signingPassword,'consumer.json':JSON.stringify({tenants:tenants.map(({project,token})=>({project,token}))})};
 for(const [name,raw]of Object.entries(material))await writeFile(join(secrets,name),raw,{mode:0o600});
 const helper=launch('secrets',apiImage,['-c','sleep 300'],['--user','0','--entrypoint','/bin/sh','--mount','type=volume,source='+secretVolume+',target=/run/secrets','--mount','type=volume,source='+workVolume+',target=/work','-e','COSIGN_PASSWORD']);
 for(const name of Object.keys(material))cmd(['cp',join(secrets,name),helper+':/run/secrets/'+name]);
 cmd(['exec',helper,'chown','-R','1000:1000','/run/secrets','/work']);
 cmd(['exec','--user','1000:1000','-e','COSIGN_PASSWORD',helper,'/usr/local/bin/cosign','generate-key-pair','--output-key-prefix','/run/secrets/custody']);
 cmd(['exec','--user','1000:1000',helper,'/usr/local/bin/cosign','signing-config','create','--out','/run/secrets/signing.json']);
 cmd(['exec','--user','1000:1000',helper,'/usr/local/bin/cosign','trusted-root','create','--out','/run/secrets/trusted-root.json']);
 const api=launch('api',apiImage,[],['--memory','1536m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/work/api-custody:rw,mode=1777,size=64m','--mount','type=volume,source='+secretVolume+',target=/run/secrets,readonly','--mount','type=volume,source='+workVolume+',target=/fixture','-e','API_S3_ENDPOINT=http://s3-fixture:8333','-e','API_S3_REGION=us-east-1','-e','API_S3_BUCKET='+bucket,'-e','API_OIDC_ISSUER=http://keycloak:8080/realms/sdk','-e','API_OIDC_AUDIENCE=sdk-api','-e','API_OIDC_JWKS=http://keycloak:8080/realms/sdk/protocol/openid-connect/certs','-e','EVIDENCE_MAX_ARTIFACT_BYTES=8388608','-p','127.0.0.1::3000']);
 const apiUrl='http://127.0.0.1:'+port(api,3000);
 await eventually(()=>http(apiUrl+'/projects/'+tenants[0].project+'/branches?name=main',{headers:{Authorization:'Bearer '+tenants[0].token}}));
 const foreign=await fetch(apiUrl+'/projects/'+tenants[1].project+'/branches?name=main',{headers:{Authorization:'Bearer '+tenants[0].token}});assert.equal(foreign.status,404);
 report.steps.push({name:'actual-API-JWT-and-cross-project-refusal',foreignStatus:foreign.status});
 const countsBefore=await apiAdmin.query('SELECT (SELECT count(*) FROM api.batches)::int AS batches,(SELECT count(*) FROM api.jobs)::int AS jobs,(SELECT count(*) FROM api.uploads)::int AS uploads');
 const admission=[];
 async function rejected(name,path,options,status){
  const response=await fetch(apiUrl+path,options);assert.equal(response.status,status);admission.push({name,status});
 }
 const branchPath='/projects/'+tenants[0].project+'/branches?name=main';
 await rejected('missing-bearer',branchPath,{},401);
 await rejected('real-Keycloak-wrong-issuer-and-audience',branchPath,{headers:{Authorization:'Bearer '+admin.access_token}},401);
 const pieces=tenants[0].token.split('.');
 pieces[2]=(pieces[2][0]==='a'?'b':'a')+pieces[2].slice(1);
 await rejected('changed-RS256-signature',branchPath,{headers:{Authorization:'Bearer '+pieces.join('.')}},401);
 await http(adminApi('sdk/users/'+tenants[1].accountId+'/role-mappings/clients/'+apiClient.id),{method:'DELETE',headers:auth,body:JSON.stringify([role])});
 const noRole=await http(kcUrl+'/realms/sdk/protocol/openid-connect/token',{method:'POST',body:new URLSearchParams({grant_type:'client_credentials',client_id:tenants[1].clientId,client_secret:tenants[1].clientSecret})});
 privateValues.push(noRole.access_token);
 await rejected('real-Keycloak-missing-required-role',branchPath,{headers:{Authorization:'Bearer '+noRole.access_token}},401);
 await http(adminApi('sdk/users/'+tenants[1].accountId+'/role-mappings/clients/'+apiClient.id),{method:'POST',headers:auth,body:JSON.stringify([role])});
 await http(adminApi('sdk'),{method:'PUT',headers:auth,body:JSON.stringify({accessTokenLifespan:1})});
 const expiring=await http(kcUrl+'/realms/sdk/protocol/openid-connect/token',{method:'POST',body:new URLSearchParams({grant_type:'client_credentials',client_id:tenants[0].clientId,client_secret:tenants[0].clientSecret})});
 privateValues.push(expiring.access_token);
 await new Promise(resolve=>setTimeout(resolve,2500));
 await rejected('real-Keycloak-expired-token',branchPath,{headers:{Authorization:'Bearer '+expiring.access_token}},401);
 await http(adminApi('sdk'),{method:'PUT',headers:auth,body:JSON.stringify({accessTokenLifespan:300})});
 const admissionHeaders={Authorization:'Bearer '+tenants[0].token,'Content-Type':'application/json'};
 await rejected('foreign-project-before-create','/projects/'+tenants[1].project+'/batches/light',{method:'POST',headers:admissionHeaders,body:JSON.stringify({branchID:tenants[1].branch})},404);
 await rejected('foreign-branch-before-create','/projects/'+tenants[0].project+'/batches/light',{method:'POST',headers:admissionHeaders,body:JSON.stringify({branchID:tenants[1].branch})},404);
 await rejected('unknown-field-before-create','/projects/'+tenants[0].project+'/batches/light',{method:'POST',headers:admissionHeaders,body:JSON.stringify({branchID:tenants[0].branch,unexpected:true})},400);
 const countsAfter=await apiAdmin.query('SELECT (SELECT count(*) FROM api.batches)::int AS batches,(SELECT count(*) FROM api.jobs)::int AS jobs,(SELECT count(*) FROM api.uploads)::int AS uploads');
 assert.deepEqual(countsAfter.rows,countsBefore.rows);
 report.steps.push({name:'actual-JWT-and-admission-refusals-before-DB-effects',cases:admission,countsUnchanged:true});

 const proxy=launch('proxy',sdkImage,['/opt/sdk/fault-proxy.mjs'],['--entrypoint','/usr/local/bin/node','--memory','128m','--mount','type=volume,source='+workVolume+',target=/work','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges']);
 const consumerCommand='for attempt in $(seq 1 300); do if [ -f /work/network-ready ]; then exec /opt/contracts/bin/python /opt/sdk/sdk-consumer.py; fi; sleep 0.1; done; exit 124';
 const consumer=launch('consumer',sdkImage,['--','/bin/sh','-c',consumerCommand],['--entrypoint','/usr/local/bin/catatonit','--memory','384m','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--mount','type=volume,source='+secretVolume+',target=/run/secrets,readonly','--mount','type=volume,source='+workVolume+',target=/work','-e','HTTP_PROXY=http://proxy:8080','-e','HTTPS_PROXY=http://proxy:8080','-e','NO_PROXY=']);
 const topology=[];
 for(const [name,expected,portNumber]of [[pg,[network,bootstrap],5432],[kc,[network,bootstrap],8080],[seaweed,[network,bootstrap],8333],[api,[network,bootstrap],3000],[proxy,[network],null],[consumer,[network],null]]){
  const detail=JSON.parse(cmd(['inspect',name]))[0];
  assert.deepEqual(Object.keys(detail.NetworkSettings.Networks).sort(),[...expected].sort());
  const bindings=portNumber?detail.NetworkSettings.Ports[portNumber+'/tcp']:null;
  if(bindings){assert.equal(bindings.length,1);assert.equal(bindings[0].HostIp,'127.0.0.1');assert.match(bindings[0].HostPort,/^[0-9]+$/)}
  if(portNumber)assert.ok(bindings);
  topology.push({name,networks:expected,loopbackBindings:bindings});
 }
 for(const name of [proxy,consumer]){
  const routes=cmd(['exec',name,'/usr/local/bin/node','-e',"process.stdout.write(require('node:fs').readFileSync('/proc/net/route','utf8'))"]);
  const rows=routes.trim().split('\n').slice(1).map(line=>line.trim().split(/\s+/));
  assert.ok(rows.every(row=>row[1]!=='00000000'),'SDK/proxy must have no default IPv4 route');
 }
 for(const item of networks){
  const d=JSON.parse(cmd(['network','inspect',item.name]))[0];
  assert.equal(d.Id??d.id,item.id);assert.equal(d.Internal??d.internal,item.internal);
  const labels=d.Labels??d.labels;
  assert.equal(labels['org.robotics.runtime.fixture-owner'],owner);assert.equal(labels['org.robotics.runtime.fixture-suite'],suite);
 }
 report.steps.push({name:'owned-two-network-bootstrap-and-isolated-SDK-proxy',topology,SDKAndProxyInternalOnly:true,noDefaultIPv4Route:true});
 cmd(['exec',proxy,'/usr/local/bin/node','-e',"require('node:fs').writeFileSync('/work/network-ready','ready\\n')"]);
 async function captureConsumerRefusal(reason){
  const detail=JSON.parse(cmd(['inspect',consumer]))[0];
  report.consumerFailure={reason,image:detail.Image,state:{status:detail.State.Status,running:detail.State.Running,
   exitCode:detail.State.ExitCode,oomKilled:detail.State.OOMKilled,startedAt:detail.State.StartedAt,finishedAt:detail.State.FinishedAt}};
  const registered=await apiAdmin.query('SELECT id,job_id,checksum,size_bytes,media_type,object_key,version_id FROM api.uploads ORDER BY id');
  report.objectIdentity=[];
  for(const row of registered.rows){
   try{
    const head=await s3.send(new HeadObjectCommand({Bucket:bucket,Key:row.object_key,ChecksumMode:'ENABLED'}),{abortSignal:AbortSignal.timeout(10000)});
    report.objectIdentity.push({registered:row,head:{version:head.VersionId,size:head.ContentLength,media:head.ContentType,checksum:head.ChecksumSHA256,metadata:head.Metadata}});
   }catch(error){report.objectIdentity.push({registered:row,errorName:error.name,status:error.$metadata?.httpStatusCode})}
  }
  await retainDiagnostic(output,'consumer-failure.log',logs(consumer),privateValues);
  await retainDiagnostic(output,'api-failure.log',logs(api),privateValues);
  report.custodyProgress=(await apiAdmin.query('SELECT u.id,u.job_id,u.version_id,u.retained_at,j.close_status,j.closed_at,(SELECT count(*) FROM api.upload_proofs p WHERE p.upload_id=u.id) AS proof_count FROM api.uploads u JOIN api.jobs j ON j.id=u.job_id ORDER BY u.id')).rows;
  const events=cmd(['exec',api,'/usr/local/bin/node','-e',"const fs=require('node:fs');const p='/fixture/cli-attempts.jsonl';if(fs.existsSync(p))process.stdout.write(fs.readFileSync(p,'utf8'))"]);
  if(events)await writeFile(join(output,'cli-attempts.jsonl'),events+'\n');
 }
 async function preserveConsumerRefusal(reason){
  report.consumerRefusal=reason;
  try{await captureConsumerRefusal(reason)}
  catch(error){report.diagnosticCaptureFailure={errorName:error.name,errorCode:error.code??null}}
 }
 let exit;
 try{exit=await eventually(async()=>{const detail=JSON.parse(cmd(['inspect',consumer]))[0];if(detail.State.Running)throw new Error('consumer active');return detail.State.ExitCode})}
 catch(error){await preserveConsumerRefusal('settlement-wait-refused');throw error}
 if(exit!==0){await preserveConsumerRefusal('settled-nonzero');throw new Error('installed SDK consumer exited '+exit)}
 cmd(['cp',consumer+':/work/sdk-report.json',join(output,'sdk-report.json')]);const sdk=JSON.parse(await readFile(join(output,'sdk-report.json'),'utf8'));assert.equal(sdk.tenants.length,2);
 const records=await apiAdmin.query('SELECT j.id,j.close_status,j.closed_at,u.id AS upload_id,u.file_name,u.checksum,u.version_id,u.retained_at,(SELECT count(*) FROM api.upload_proofs p WHERE p.upload_id=u.id) AS proof_count FROM api.jobs j JOIN api.uploads u ON u.job_id=j.id ORDER BY j.id,u.file_name');
 assert.equal(records.rows.length,6);assert.ok(records.rows.every(r=>r.close_status==='SUCCEEDED'&&r.closed_at&&r.retained_at&&r.version_id&&Number(r.proof_count)===5));
 const custody=join(output,'custody');await mkdir(custody);
 async function captureUploads(uploads,destination){
 const witnesses=[];
 for(const upload of uploads){
  const dir=join(destination,upload.id);await mkdir(dir);
  const size=Number(upload.size_bytes);
  const response=await s3.send(new GetObjectCommand({Bucket:bucket,Key:upload.object_key,VersionId:upload.version_id,...(size?{Range:'bytes=0-'+size}:{})}),{abortSignal:AbortSignal.timeout(10000)});
  const parts=[];for await(const part of response.Body)parts.push(Buffer.from(part));const raw=Buffer.concat(parts);
  assert.equal(raw.length,size);assert.equal(createHash('sha256').update(raw).digest('hex'),upload.checksum);
  assert.equal(response.VersionId,upload.version_id);assert.equal(response.ContentType,upload.media_type);
  assert.equal(response.ContentRange,size?'bytes 0-'+(size-1)+'/'+size:undefined);
  await writeFile(join(dir,'payload'),raw);
  await writeFile(join(dir,'object.json'),JSON.stringify({registered:upload,response:{version:response.VersionId,size:response.ContentLength,media:response.ContentType,range:response.ContentRange,metadata:response.Metadata}},null,2)+'\n');
  const proofs=await apiAdmin.query('SELECT role,raw,sha256 FROM api.upload_proofs WHERE upload_id=$1 ORDER BY role',[upload.id]);
  const files=[];
  for(const proof of proofs.rows){
   assert.equal(createHash('sha256').update(proof.raw).digest('hex'),proof.sha256);
   await writeFile(join(dir,proof.role),proof.raw);
   files.push({role:proof.role,sha256:proof.sha256,size:proof.raw.length});
  }
  witnesses.push({upload:upload.id,payload:{sha256:upload.checksum,size},files,exactVersionReadback:true,emptySuccessfulEOF:size===0});
 }
 return witnesses;
 }
 const uploads=await apiAdmin.query('SELECT * FROM api.uploads ORDER BY id');
 report.witnesses=await captureUploads(uploads.rows,custody);
 for(const name of ['custody.pub','signing.json','trusted-root.json'])cmd(['cp',helper+':/run/secrets/'+name,join(custody,name)]);
 for(const tenant of sdk.tenants)cmd(['cp',consumer+':/work/emissions_'+tenant.job+'.resim.jsonl',join(custody,'sdk-emissions-'+tenant.job+'.jsonl')]);
 cmd(['cp',consumer+':/work/attachment.png',join(custody,'sdk-attachment.png')]);
 cmd(['cp',consumer+':/work/empty.log',join(custody,'sdk-empty.log')]);
 report.steps.push({name:'installed-unmodified-SDK-Batch-Test-two-tenants',jobs:2,retainedUploads:6,independentExactVersionReadback:true,preservedProofFiles:30});

 cmd(['cp',proxy+':/work/proxy-report.json',join(output,'proxy-report.json')]);const audit=JSON.parse(await readFile(join(output,'proxy-report.json'),'utf8'));assert.ok(audit.droppedLog&&audit.droppedClose);assert.ok(audit.observations.every(r=>audit.permitted.includes(r.host)&&!r.refused));
 report.steps.push({name:'actual-request-allowlist-and-lost-response-log-close',requests:audit.observations.length});
 const headers={Authorization:'Bearer '+tenants[0].token,'Content-Type':'application/json'};
 async function post(path,body){return http(apiUrl+path,{method:'POST',headers,...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.timeout(120000)})}
 const batch=await post('/projects/'+tenants[0].project+'/batches/light',{branchID:tenants[0].branch,batchName:'Concurrency'});
 const closePaths=[];
 for(let index=0;index<8;index++){
  const base='/projects/'+tenants[0].project+'/batches/'+batch.batchID;
  const job=await post(base+'/jobs',{name:'concurrent-'+index});
  const raw=Buffer.from('concurrent custody '+index+'\n'),checksum=createHash('sha256').update(raw).digest('hex');
  const log=await post(base+'/jobs/'+job.jobID+'/logs',{fileName:'pool.log',fileSize:raw.length,checksum,logType:'OTHER_LOG'});
  const url=new URL(log.uploadURL);
  const upload=await new Promise((resolve,reject)=>{
   const request=wireRequest({hostname:'127.0.0.1',port:port(seaweed,8333),path:url.pathname+url.search,method:'PUT',
    headers:{...log.requiredHeaders,Host:url.host,'Content-Length':String(raw.length)}},response=>{response.resume();response.once('end',()=>resolve(response.statusCode))});
   request.once('error',reject);request.end(raw);
  });
  assert.equal(upload,200);closePaths.push(base+'/jobs/'+job.jobID+'/close');
 }
 await Promise.all(closePaths.map(path=>post(path,{status:'SUCCEEDED'})));
 const parallel=await apiAdmin.query('SELECT count(*)::int AS closed FROM api.jobs WHERE batch_id=$1 AND closed_at IS NOT NULL',[batch.batchID]);
 assert.equal(parallel.rows[0].closed,8);
 const parallelUploads=await apiAdmin.query('SELECT * FROM api.uploads WHERE batch_id=$1 ORDER BY id',[batch.batchID]);
 const parallelDirectory=join(output,'concurrency');await mkdir(parallelDirectory);
 report.concurrencyWitnesses=await captureUploads(parallelUploads.rows,parallelDirectory);
 report.steps.push({name:'eight-concurrent-real-custody-closes-pool-max8',closed:8,preservedProofFiles:40,exactVersionReadbacks:8});
 const recoveryBatch=await post('/projects/'+tenants[0].project+'/batches/light',{branchID:tenants[0].branch,batchName:'Recovery'});
 const recoveryBase='/projects/'+tenants[0].project+'/batches/'+recoveryBatch.batchID;
 const recoveryJob=await post(recoveryBase+'/jobs',{name:'two-upload recovery'});
 const recoveryLogs=[];
 for(const name of ['first.log','second.log']){
  const raw=Buffer.from('custody recovery '+name+'\n'),checksum=createHash('sha256').update(raw).digest('hex');
  const value=await post(recoveryBase+'/jobs/'+recoveryJob.jobID+'/logs',{fileName:name,fileSize:raw.length,checksum,logType:'OTHER_LOG'});
  recoveryLogs.push({value,raw,identity:{fileName:name,fileSize:raw.length,checksum,logType:'OTHER_LOG'}});
 }
 recoveryLogs.sort((a,b)=>a.value.logID.localeCompare(b.value.logID));
 const uploadCountBefore=(await apiAdmin.query('SELECT count(*)::int AS total FROM api.uploads')).rows[0].total;
 const guardCases=[
  {name:'oversize-before-presign',body:{...recoveryLogs[0].identity,fileName:'large.log',fileSize:8388609}},
  {name:'negative-size-before-presign',body:{...recoveryLogs[0].identity,fileName:'negative.log',fileSize:-1}},
  {name:'string-size-no-coercion',body:{...recoveryLogs[0].identity,fileName:'string.log',fileSize:String(recoveryLogs[0].raw.length)}},
  {name:'unknown-upload-input',body:{...recoveryLogs[0].identity,arbitraryURI:'s3://foreign/payload'}},
 ];
 for(const test of guardCases){
  const response=await fetch(apiUrl+recoveryBase+'/jobs/'+recoveryJob.jobID+'/logs',{method:'POST',headers,body:JSON.stringify(test.body)});
  assert.equal(response.status,400);
 }
 const uploadCountAfter=(await apiAdmin.query('SELECT count(*)::int AS total FROM api.uploads')).rows[0].total;
 assert.equal(uploadCountAfter,uploadCountBefore);
 report.steps.push({name:'strict-upload-inputs-before-registration-and-presign',cases:guardCases.map(({name})=>({name,status:400})),uploadCountUnchanged:true});

 async function putRecovery(log){
  const url=new URL(log.value.uploadURL);
  const status=await new Promise((resolve,reject)=>{
   const request=wireRequest({hostname:'127.0.0.1',port:port(seaweed,8333),path:url.pathname+url.search,method:'PUT',
    headers:{...log.value.requiredHeaders,Host:url.host,'Content-Length':String(log.raw.length)}},response=>{response.resume();response.once('end',()=>resolve(response.statusCode))});
   request.once('error',reject);request.end(log.raw);
  });assert.equal(status,200);
 }
 await putRecovery(recoveryLogs[0]);
 const incomplete=await fetch(apiUrl+recoveryBase+'/jobs/'+recoveryJob.jobID+'/close',{method:'POST',headers,
  body:JSON.stringify({status:'ERROR',errorMessage:'producer reports the interrupted upload'}),signal:AbortSignal.timeout(120000)});
 assert.equal(incomplete.status,503);
 const before=await apiAdmin.query('SELECT u.id,u.version_id,u.retained_at::text AS retained_time,p.role,p.sha256,p.raw FROM api.uploads u LEFT JOIN api.upload_proofs p ON p.upload_id=u.id WHERE u.job_id=$1 ORDER BY u.id,p.role',[recoveryJob.jobID]);
 const firstBefore=before.rows.filter(r=>r.id===recoveryLogs[0].value.logID);assert.equal(firstBefore.length,5);assert.ok(firstBefore.every(r=>r.retained_time));
 const secondBefore=before.rows.filter(r=>r.id===recoveryLogs[1].value.logID);assert.equal(secondBefore.length,1);assert.equal(secondBefore[0].retained_time,null);
 const claimBefore=await apiAdmin.query('SELECT close_status,close_error,closed_at FROM api.jobs WHERE id=$1',[recoveryJob.jobID]);
 assert.equal(claimBefore.rows[0].close_status,'ERROR');assert.equal(claimBefore.rows[0].closed_at,null);
 const dir=join(output,'recovery');await mkdir(dir);
 for(const proof of firstBefore)await writeFile(join(dir,'before-'+proof.role),proof.raw);
 await writeFile(join(dir,'before.json'),JSON.stringify({uploads:before.rows.map(({raw,...r})=>r),claim:claimBefore.rows[0]},null,2)+'\n');
 cmd(['stop','--time','15',api]);const stopped=JSON.parse(cmd(['inspect',api]))[0];assert.equal(stopped.State.Running,false);
 cmd(['start',api]);await eventually(()=>http(apiUrl+'/projects/'+tenants[0].project+'/branches?name=main',{headers:{Authorization:'Bearer '+tenants[0].token}}));
 const renewed=await post(recoveryBase+'/jobs/'+recoveryJob.jobID+'/logs',recoveryLogs[1].identity);
 assert.equal(renewed.logID,recoveryLogs[1].value.logID);
 assert.equal(new URL(renewed.uploadURL).pathname,new URL(recoveryLogs[1].value.uploadURL).pathname);
 recoveryLogs[1].value=renewed;
 const refusalCases=[
  {name:'new-log-after-close-claim',body:{...recoveryLogs[1].identity,fileName:'third.log'},status:400},
  {name:'changed-identity-after-close-claim',body:{...recoveryLogs[1].identity,checksum:'0'.repeat(64)},status:409},
  {name:'bound-first-upload-renewal',body:recoveryLogs[0].identity,status:400},
 ];
 for(const test of refusalCases){
  const response=await fetch(apiUrl+recoveryBase+'/jobs/'+recoveryJob.jobID+'/logs',{method:'POST',headers,body:JSON.stringify(test.body)});
  assert.equal(response.status,test.status);
 }
 await putRecovery(recoveryLogs[1]);
 await post(recoveryBase+'/jobs/'+recoveryJob.jobID+'/close',{status:'ERROR',errorMessage:'producer reports the interrupted upload'});
 const after=await apiAdmin.query('SELECT u.id,u.version_id,u.retained_at::text AS retained_time,p.role,p.sha256,p.raw FROM api.uploads u JOIN api.upload_proofs p ON p.upload_id=u.id WHERE u.job_id=$1 ORDER BY u.id,p.role',[recoveryJob.jobID]);
 const firstAfter=after.rows.filter(r=>r.id===recoveryLogs[0].value.logID);
 assert.deepEqual(firstAfter.map(({raw,...r})=>r),firstBefore.map(({raw,...r})=>r));
 for(let i=0;i<firstBefore.length;i++)assert.ok(firstBefore[i].raw.equals(firstAfter[i].raw));
 assert.equal(after.rows.length,10);
 const claimAfter=await apiAdmin.query('SELECT close_status,close_error,closed_at FROM api.jobs WHERE id=$1',[recoveryJob.jobID]);
 assert.equal(claimAfter.rows[0].close_status,'ERROR');assert.equal(claimAfter.rows[0].close_error,claimBefore.rows[0].close_error);assert.ok(claimAfter.rows[0].closed_at);
 for(const proof of after.rows)await writeFile(join(dir,'after-'+proof.id+'-'+proof.role),proof.raw);
 await writeFile(join(dir,'after.json'),JSON.stringify({uploads:after.rows.map(({raw,...r})=>r),claim:claimAfter.rows[0]},null,2)+'\n');
 const recoveryUploads=await apiAdmin.query('SELECT * FROM api.uploads WHERE job_id=$1 ORDER BY id',[recoveryJob.jobID]);
 report.recoveryWitnesses=await captureUploads(recoveryUploads.rows,dir);
 report.steps.push({name:'two-upload-first-real-custody-second-S3-refusal-restart-retry',initialClose:503,firstProofBytesAndTimestampUnchanged:true,
  secondCompleted:true,claimedStatusPreserved:'ERROR',actualApiRestart:true,unboundSameIdentityRenewal:true,refusalCases});
 cmd(['cp',api+':/fixture/cli-attempts.jsonl',join(output,'cli-attempts.jsonl')]);
 const attempts=(await readFile(join(output,'cli-attempts.jsonl'),'utf8')).trim().split('\n').map(line=>JSON.parse(line));
 const counts={};
 for(const event of attempts){const key=event.upload+':'+event.operation;counts[key]=(counts[key]??0)+1}
 const allUploads=[...uploads.rows,...parallelUploads.rows,...recoveryUploads.rows];
 assert.equal(allUploads.length,16);
 for(const upload of allUploads)for(const operation of ['predicate','verify'])assert.equal(counts[upload.id+':'+operation],1);
 assert.equal(attempts.length,32);
 report.custodyAttempts={events:32,uploads:16,eachPredicateAndVerifyExactlyOnce:true,counts};
 report.images=Object.fromEntries([apiImage,sdkImage,lock.node,lock.postgres,lock.keycloak,lock.s3].map(image=>{const d=JSON.parse(cmd(['image','inspect',image]))[0];return[image,{id:d.Id,digest:d.Digest}]}));
 report.toolVersions={node:cmd(['exec',api,'node','--version']),aws:cmd(['exec',api,'aws','--version']),cosign:cmd(['exec',api,'cosign','version','--json']),postgres:(await apiAdmin.query('SHOW server_version')).rows[0].server_version};
 report.records=records.rows;report.passed=true;


}catch(error){report.passed=false;report.error=redactDiagnostics(String(error),privateValues);process.exitCode=1}
finally{
 await apiAdmin?.end();await pgAdmin?.end();s3?.destroy();
 for(const name of names.reverse()){try{const d=JSON.parse(cmd(['inspect',name]))[0];assert.equal(d.Config.Labels['org.robotics.runtime.fixture-owner'],owner);cmd(['stop','--time','15',name]);cmd(['rm',name])}catch(e){report.cleanupError=String(e)}}
 for(const name of volumes.reverse()){try{const d=JSON.parse(cmd(['volume','inspect',name]))[0];assert.equal(d.Labels['org.robotics.runtime.fixture-owner'],owner);cmd(['volume','rm',name])}catch(e){report.cleanupError=String(e)}}
 for(const item of networks.reverse()){
  try{
   const d=JSON.parse(cmd(['network','inspect',item.name]))[0],labels=d.Labels??d.labels;
   assert.equal(d.Id??d.id,item.id);assert.equal(labels['org.robotics.runtime.fixture-owner'],owner);assert.equal(labels['org.robotics.runtime.fixture-suite'],suite);
   cmd(['network','rm',item.id]);
  }catch(e){report.cleanupError=String(e)}
 }

 await rm(secrets,{recursive:true,force:true});
 if(report.cleanupError){report.passed=false;process.exitCode=1}
 const reportBytes=Buffer.from(JSON.stringify(report,null,2)+'\n');assertSafeArtifact(reportBytes,privateValues);
 await writeFile(join(output,'gateway-report.json'),reportBytes);console.log(JSON.stringify({passed:report.passed,steps:report.steps,error:report.error,cleanupError:report.cleanupError}));
}
