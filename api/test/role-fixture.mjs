import assert from 'node:assert/strict';
import {randomUUID,randomBytes} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {Pool} from 'pg';
import {verifyApplicationRole,transaction} from '../dist/src/database.js';
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
 app=new Pool({host:'127.0.0.1',port,user:'api_app',password,database:'postgres',max:8,connectionTimeoutMillis:5000});
 await verifyApplicationRole(app);report.steps.push({name:'baseline-guard',passed:true});
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
