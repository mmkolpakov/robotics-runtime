import assert from 'node:assert/strict';
import {randomUUID,randomBytes,createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {Pool} from 'pg';
import {verifyApplicationRole,transaction} from '../dist/src/database.js';
import {Domain} from '../dist/src/domain.js';
const lock=JSON.parse(await readFile(new URL('./upstream-lock.json',import.meta.url),'utf8'));
const owner='rr-api-pg-'+randomUUID().slice(0,8),volume=owner+'-data',password=randomBytes(24).toString('hex');
const environment={...process.env,POSTGRES_PASSWORD:password};
const engine=process.env.API_FIXTURE_ENGINE??'podman',suite=process.env.API_FIXTURE_SUITE??owner;
assert.ok(['podman','docker'].includes(engine));assert.match(suite,/^[a-z0-9-]{1,80}$/);
const output=new URL('../../artifacts/'+owner+'/',import.meta.url);await mkdir(output,{recursive:true});
await writeFile(new URL('fixture-owner.json',output),JSON.stringify({owner,suite})+'\n');
const report={engine,scope:'Actual PostgreSQL18.6 RLS and role-closure regression; no SDK/JWT or API acceptance',owner,steps:[]};
const command=args=>{const p=spawnSync(engine,args,{env:environment,encoding:'utf8',timeout:60000});if(p.status!==0)throw new Error(args[0]+' failed: '+p.stderr);return p.stdout.trim()};
let admin,app;
try{
 command(['volume','create','--label','org.robotics.runtime.fixture-owner='+owner,'--label','org.robotics.runtime.fixture-suite='+suite,volume]);
 command(['run','--detach','--name',owner,'--label','org.robotics.runtime.fixture-owner='+owner,'--label','org.robotics.runtime.fixture-suite='+suite,'--memory','256m',
  '-e','POSTGRES_PASSWORD','-p','127.0.0.1::5432','--mount','type=volume,source='+volume+',target=/var/lib/postgresql',lock.postgres]);
 const port=Number(command(['port',owner,'5432/tcp']).split(':').at(-1));
 admin=new Pool({host:'127.0.0.1',port,user:'postgres',password,database:'postgres',max:2,connectionTimeoutMillis:1000});
 for(let i=0;i<100;i++){try{await admin.query('SELECT 1');break}catch{await new Promise(r=>setTimeout(r,100))}}
 await admin.query('CREATE ROLE api_owner NOLOGIN');
 await admin.query("CREATE ROLE api_app LOGIN PASSWORD '"+password+"'");
 await admin.query(await readFile(new URL('../sql/001-external-tests.sql',import.meta.url),'utf8'));
 await admin.query(await readFile(new URL('../sql/002-metrics-config.sql',import.meta.url),'utf8'));
 app=new Pool({host:'127.0.0.1',port,user:'api_app',password,database:'postgres',max:8,connectionTimeoutMillis:5000});
 await verifyApplicationRole(app);report.steps.push({name:'baseline-guard',passed:true});
 report.postgresVersion=(await admin.query('SELECT version() AS version')).rows[0].version;
 report.postgresImage=JSON.parse(command(['inspect',owner]))[0].Image;

 const a='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',b='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
 const pa='11111111-1111-4111-8111-111111111111',pb='22222222-2222-4222-8222-222222222222';
 await admin.query('INSERT INTO api.tenants(id) VALUES($1),($2)',[a,b]);
 await admin.query('INSERT INTO api.memberships VALUES($1,$2,$3,$4,$5),($6,$2,$7,$8,$9)',
  [a,'fixture-issuer','subject-a','account-a',pa,b,'subject-b','account-b',pb]);
 await admin.query("INSERT INTO api.projects VALUES($1,$2,'A'),($3,$4,'B')",[a,pa,b,pb]);
 await admin.query('INSERT INTO api.project_memberships VALUES($1,$2,$3,$4),($5,$6,$3,$7)',[a,pa,'fixture-issuer','subject-a',b,pb,'subject-b']);
 const count=principal=>transaction(app,principal,c=>c.query('SELECT id FROM api.projects ORDER BY id'));
 assert.deepEqual((await count({issuer:'fixture-issuer',subject:'subject-a'})).rows.map(r=>r.id),[pa]);
 assert.deepEqual((await count({issuer:'fixture-issuer',subject:'subject-b'})).rows.map(r=>r.id),[pb]);
 assert.equal((await app.query('SELECT id FROM api.projects')).rows.length,0);
 report.steps.push({name:'two-principal-project-RLS-and-local-setting-reset',passed:true});
 const principalA={issuer:'fixture-issuer',subject:'subject-a'},principalB={issuer:'fixture-issuer',subject:'subject-b'};
 const branchA='33333333-3333-4333-8333-333333333333',branchB='44444444-4444-4444-8444-444444444444';
 await admin.query("INSERT INTO api.branches(tenant_id,project_id,id,name,branch_type,created_by) VALUES($1,$2,$3,'main','MAIN',$2),($4,$5,$6,'main','MAIN',$5)",[a,pa,branchA,b,pb,branchB]);
 const domain=new Domain(app,{},{}),signal=()=>AbortSignal.timeout(10000);
 const config=(projectId,raw)=>({projectId,branch:'main',config:Buffer.from(raw).toString('base64'),templateFiles:[{name:'opaque.liquid',contents:Buffer.from('{% include "/etc/passwd" %}').toString('base64')}]});
 const first=await domain.updateMetricsConfig(principalA,config(pa,'first\n'),signal());
 assert.equal(await domain.updateMetricsConfig(principalA,config(pa,'first\n'),signal()),first);
 await assert.rejects(domain.updateMetricsConfig(principalA,config(pb,'foreign'),signal()),/project not found/);
 await assert.rejects(domain.updateMetricsConfig(principalA,{...config(pa,'missing'),branch:'missing'},signal()),/branch not found/);
 assert.equal((await admin.query('SELECT id FROM api.config_snapshots')).rowCount,1);
 assert.equal((await transaction(app,principalB,c=>c.query('SELECT id FROM api.config_snapshots'))).rowCount,0);

 const original=await domain.createBatch(principalA,pa,{branchID:branchA});
 const originalSnapshot=(await admin.query('SELECT config_snapshot_id FROM api.batches WHERE id=$1',[original.batchID])).rows[0].config_snapshot_id;assert.equal(originalSnapshot,first);
 const concurrent=await Promise.all([domain.updateMetricsConfig(principalA,config(pa,'second\n'),signal()),domain.createBatch(principalA,pa,{branchID:branchA}),domain.updateMetricsConfig(principalA,config(pa,'third\n'),signal())]);
 const pinned=(await admin.query('SELECT b.config_snapshot_id,s.config FROM api.batches b JOIN api.config_snapshots s ON s.tenant_id=b.tenant_id AND s.project_id=b.project_id AND s.branch_id=b.branch_id AND s.id=b.config_snapshot_id WHERE b.id=$1',[concurrent[1].batchID])).rows[0];
 assert.ok([first,concurrent[0],concurrent[2]].includes(pinned.config_snapshot_id));assert.ok(['first\n','second\n','third\n'].includes(pinned.config.toString()));
 assert.equal((await admin.query('SELECT config_snapshot_id FROM api.batches WHERE id=$1',[original.batchID])).rows[0].config_snapshot_id,first);
 const before=await admin.query('SELECT config_snapshot_id FROM api.branches WHERE id=$1',[branchA]),countBefore=(await admin.query('SELECT count(*)::int AS n FROM api.config_snapshots')).rows[0].n;
 await admin.query("CREATE FUNCTION api.fixture_refuse_config() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fixture-pointer-refusal'; END; $$; CREATE TRIGGER fixture_refuse_config BEFORE UPDATE ON api.branches FOR EACH ROW EXECUTE FUNCTION api.fixture_refuse_config()");
 await assert.rejects(domain.updateMetricsConfig(principalA,config(pa,'rolled-back\n'),signal()),/fixture-pointer-refusal/);
 await admin.query('DROP TRIGGER fixture_refuse_config ON api.branches; DROP FUNCTION api.fixture_refuse_config()');
 assert.equal((await admin.query('SELECT count(*)::int AS n FROM api.config_snapshots')).rows[0].n,countBefore);
 assert.equal((await admin.query('SELECT config_snapshot_id FROM api.branches WHERE id=$1',[branchA])).rows[0].config_snapshot_id,before.rows[0].config_snapshot_id);
 await assert.rejects(transaction(app,principalA,c=>c.query("UPDATE api.config_snapshots SET config='changed' WHERE id=$1",[first])),/permission denied/);
 await assert.rejects(transaction(app,principalA,c=>c.query('DELETE FROM api.config_snapshots WHERE id=$1',[first])),/permission denied/);
 const immutable=(await admin.query('SELECT config,template_files FROM api.config_snapshots WHERE id=$1',[first])).rows[0];assert.equal(immutable.config.toString(),'first\n');assert.equal(Buffer.from(immutable.template_files[0].contents,'base64').toString(),'{% include "/etc/passwd" %}');
 report.steps.push({name:'config-snapshot-two-tenant-RLS-immutable-retry-concurrent-batch-and-real-pointer-rollback',passed:true,snapshotCount:countBefore,oldBatchSnapshot:first,concurrentBatchSnapshot:pinned.config_snapshot_id});
 await admin.query('ALTER TABLE api.config_snapshots NO FORCE ROW LEVEL SECURITY');
 try{await assert.rejects(verifyApplicationRole(app),/all metadata tables require forced RLS/)}finally{await admin.query('ALTER TABLE api.config_snapshots FORCE ROW LEVEL SECURITY')}
 // An unexpected metadata table must not be silently admitted by a count-only guard.
 await admin.query('CREATE TABLE api.unexpected_metadata(id uuid); ALTER TABLE api.unexpected_metadata ENABLE ROW LEVEL SECURITY; ALTER TABLE api.unexpected_metadata FORCE ROW LEVEL SECURITY');
 try{await assert.rejects(verifyApplicationRole(app),/all metadata tables require forced RLS/)}finally{await admin.query('DROP TABLE api.unexpected_metadata')}
 report.steps.push({name:'exact-eleven-table-and-config-FORCE-RLS-startup-inventory',passed:true});
 const rawSnapshots=(await admin.query('SELECT tenant_id,project_id,branch_id,id,config,config_sha256,template_files,snapshot_sha256,created_by,created_at FROM api.config_snapshots ORDER BY id')).rows;
 for(const row of rawSnapshots){
  assert.equal(createHash('sha256').update(row.config).digest('hex'),row.config_sha256);
  for(const file of row.template_files){const raw=Buffer.from(file.contents,'base64');assert.equal(raw.length,file.size);assert.equal(createHash('sha256').update(raw).digest('hex'),file.sha256)}
 }
 await mkdir(new URL('config/',output));
 await writeFile(new URL('config/snapshots.json',output),JSON.stringify(rawSnapshots.map(({config,...row})=>({...row,config_base64:config.toString('base64')})),null,2)+'\n');
 report.configSnapshotReadback={rows:rawSnapshots.length,byteAndTemplateSHA:true,originalSnapshot:first};


 await admin.query('GRANT api_owner TO api_app');
 const old=await app.query("SELECT r.rolsuper,r.rolbypassrls,EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='api' AND tableowner=current_user) AS owns_tables FROM pg_roles r WHERE r.rolname=current_user");
 assert.equal(old.rows[0].rolsuper,false);assert.equal(old.rows[0].rolbypassrls,false);assert.equal(old.rows[0].owns_tables,false);
 await assert.rejects(verifyApplicationRole(app),/application role must not own tables or bypass RLS/);
 const client=await app.connect();
 try{
  await client.query('BEGIN');await client.query('SET ROLE api_owner');await client.query('ALTER TABLE api.projects DISABLE ROW LEVEL SECURITY');
  const actual=await client.query("SELECT relrowsecurity FROM pg_class WHERE oid='api.projects'::regclass");assert.equal(actual.rows[0].relrowsecurity,false);
  await client.query('ROLLBACK');
 }finally{client.release()}
 report.steps.push({name:'real-GRANT-owner-SET-ROLE-disable-RLS-counterexample',oldGuardWouldPass:true,newGuardRefuses:true,actualDisableObservedAndRolledBack:true});
 await admin.query('REVOKE api_owner FROM api_app');await verifyApplicationRole(app);
 report.steps.push({name:'guard-after-membership-revocation',passed:true});
 report.passed=true;
}catch(error){report.passed=false;report.error=String(error);throw error}
finally{
 await app?.end();await admin?.end();
 try{const v=JSON.parse(command(['inspect',owner]))[0];assert.equal(v.Config.Labels['org.robotics.runtime.fixture-owner'],owner);command(['stop','--time','15',owner]);command(['rm',owner])}catch(e){report.cleanupError=String(e)}
 try{const v=JSON.parse(command(['volume','inspect',volume]))[0];assert.equal(v.Labels['org.robotics.runtime.fixture-owner'],owner);command(['volume','rm',volume])}catch(e){report.cleanupError=String(e)}
 if(report.cleanupError){report.passed=false;process.exitCode=1}
 await writeFile(new URL('role-report.json',output),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
}
