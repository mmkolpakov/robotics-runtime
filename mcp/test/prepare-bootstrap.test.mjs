import assert from 'node:assert/strict';
import {test} from 'node:test';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {chmod,copyFile,mkdir,mkdtemp,open,readFile,rm,symlink,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {createOfflineAdapter} from '../src/server.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const helper=resolve(here,'../tools/prepare-bootstrap.py');
const source=resolve(here,'../../packages/contracts/tests/fixtures/qualification/inference');
const contractsCli=process.env.MCP_TEST_CONTRACTS_CLI;
const harnessCli=process.env.MCP_TEST_HARNESS_CLI;
assert.ok(contractsCli&&harnessCli,'bootstrap tests require explicitly selected installed public workers');
const python=join(dirname(contractsCli),'python');
const environment={PATH:'/usr/bin:/bin',LANG:'C.UTF-8',PYTHONDONTWRITEBYTECODE:'1'};
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
async function inventory(f,lines){
 const path=join(f.root,'qualification-arguments.txt');
 await chmod(path,0o600).catch(()=>{});
 await writeFile(path,lines.join('\n')+'\n',{mode:0o444});
 await chmod(path,0o444);
}
async function fixture(t){
 const parent=await mkdtemp(join(tmpdir(),'mcp-prepare-'));
 t.after(()=>rm(parent,{recursive:true,force:true}));
 const root=join(parent,'package'),scratch=join(parent,'scratch');
 await mkdir(root,{mode:0o700});await mkdir(scratch,{mode:0o700});
 const entries=JSON.parse(await readFile(join(source,'artifacts.json'),'utf8'));
 const lines=[];
 for(const row of entries){
  const relative='subjects/'+row.subject_name,path=join(root,relative);
  await mkdir(dirname(path),{recursive:true});
  await copyFile(join(source,row.file),path);await chmod(path,0o444);
  lines.push('--artifact',row.kind+':'+row.subject_name+'='+relative);
 }
 const f={root,scratch,parent,entries,lines};await inventory(f,lines);return f;
}
function argv(f,domains=['primary']){
 return [helper,'--package-root',f.root,'--scratch-root',f.scratch,
  '--contracts-cli',contractsCli,'--harness-cli',harnessCli,...domains.flatMap(id=>['--domain',id])];
}
function prepare(f,domains=['primary']){
 return spawnSync(python,argv(f,domains),{env:environment,encoding:'utf8',timeout:30000,maxBuffer:1048576});
}
function accepted(result){
 assert.equal(result.status,0,result.stderr);
 return {config:JSON.parse(result.stdout),mapping:JSON.parse(result.stderr)};
}
function refused(result,reason){
 assert.equal(result.status,2,result.stderr);assert.equal(result.stdout,'');assert.match(result.stderr,reason);
}

test('published inventory becomes a relocated stable MCP catalog and works through the existing read tools',{timeout:60000},async t=>{
 const f=await fixture(t),g=await fixture(t);
 const metrics='subjects/metrics.jsonl';
 await copyFile(resolve(here,'../../packages/harness/tests/fixtures/histograms/delta.jsonl'),join(f.root,metrics));
 await chmod(join(f.root,metrics),0o444);
 f.lines.push('--artifact','metrics:metrics/primary.jsonl='+metrics);
 await inventory(f,[...f.lines,'--artifact',f.lines[1]]);
 await copyFile(join(f.root,metrics),join(g.root,metrics));await chmod(join(g.root,metrics),0o444);
 await inventory(g,[...f.lines,'--artifact',f.lines[1]]);
 const a=accepted(prepare(f)),b=accepted(prepare(g));
 assert.deepEqual(a.mapping,b.mapping);
 for(const key of ['artifacts','schemas','bundles'])assert.deepEqual(a.config[key],b.config[key]);
 assert.equal(new Set(a.config.artifacts.map(row=>row.id)).size,a.config.artifacts.length);
 assert.ok(a.config.schemas.some(row=>row.schema==='acceptance-scenario.v2'));
 assert.ok(!a.config.artifacts.some(row=>row.path.endsWith('.mcap')));
 assert.ok(a.config.bundles[0].model&&a.config.bundles[0].dataset);
 const originals=new Map();
 for(const row of a.config.artifacts){
  const bytes=await readFile(join(f.root,row.path));originals.set(row.path,bytes);
  assert.equal(row.sha256,digest(bytes));assert.equal(row.size_bytes,bytes.length);
 }
 const configPath=join(f.parent,'bootstrap.json');await writeFile(configPath,JSON.stringify(a.config));
 const transport=new StdioClientTransport({command:process.execPath,args:[resolve(here,'../bin/server.mjs'),'--config',configPath],env:{},stderr:'pipe'});
 const client=new Client({name:'prepared-bootstrap-test',version:'1.0.0'});
 t.after(async()=>{await client.close();await transport.close()});
 await client.connect(transport);
 const listed=await client.listTools();assert.equal(listed.tools.length,6);
 async function call(name,args={}){
  const response=await client.callTool({name,arguments:args});
  const value=JSON.parse(response.content[0].text);assert.equal(value.ok,true,value.stdout+value.stderr);
  return value;
 }
 await call('describe_contract',{schema_id:a.config.schemas.find(row=>row.schema==='acceptance-scenario.v1').id});
 await call('validate_documents',{artifact_ids:[a.mapping.artifact_ids['scenario.json'],a.mapping.artifact_ids['runtime-manifests/primary.json']]});
 await call('explain_bundle',{bundle_id:a.config.bundles[0].id});
 await call('explain_result',{artifact_id:a.mapping.artifact_ids['results/primary.json']});
 await call('summarize_otlp',{artifact_id:a.mapping.artifact_ids['metrics/primary.jsonl']});
 await call('inspect_offline_readiness');
 for(const [path,bytes]of originals)assert.deepEqual(await readFile(join(f.root,path)),bytes);
});

test('public loader retains YAML suffix mode and extension schemas use existing records',async t=>{
 const f=await fixture(t);
 const path='subjects/scenario.YAML',bytes=Buffer.from((await readFile(join(f.root,'subjects/scenario.json'),'utf8')).replace('"schema_version":','schema_version: '));
 await writeFile(join(f.root,path),bytes,{mode:0o444});
 const schema=await readFile(join(here,'fixtures/nav2.schema.json'));
 const uri=JSON.parse(schema).$id;
 await writeFile(join(f.root,'extension.json'),schema,{mode:0o444});
 const lines=f.lines.map(line=>line==='scenario:scenario.json=subjects/scenario.json'?'scenario:scenario.json='+path:line);
 await inventory(f,[...lines,'--extension-schema',uri+'=extension.json']);
 const {config,mapping}=accepted(prepare(f));
 assert.equal(config.artifacts.find(row=>row.id===mapping.artifact_ids['scenario.json']).sha256,digest(bytes));
 assert.equal(config.extensionSchemas[0].uri,uri);
 const adapter=await createOfflineAdapter(config);await adapter.close();
 await inventory(f,lines.map(line=>line.endsWith('='+path)?line.replace(path,'subjects/scenario.json'):line));
 await chmod(join(f.root,'subjects/scenario.json'),0o600);
 await writeFile(join(f.root,'subjects/scenario.json'),bytes);await chmod(join(f.root,'subjects/scenario.json'),0o444);
 refused(prepare(f),/parse|JSON/i);
});

test('literal inventory refuses imported commands, response files, traversal, links and nonregular files',async t=>{
 const f=await fixture(t);
 for(const extra of [['--contracts-cli','/bin/sh'],['--env','PAYLOAD=x'],['@more-arguments'],['--art','recording:x=subjects/scenario.json']]){
  await inventory(f,[...f.lines,...extra]);refused(prepare(f),/inventory arguments/);
 }
 for(const relative of ['../outside.json','/etc/passwd','subjects/../scenario.json']){
  await inventory(f,[...f.lines,'--artifact','metrics:metrics/escape='+relative]);
  refused(prepare(f),/relative|canonical/);
 }
 await symlink(join(f.root,'subjects/scenario.json'),join(f.root,'linked.json'));
 await inventory(f,[...f.lines,'--artifact','metrics:metrics/link=linked.json']);
 refused(prepare(f),/link/);
 await symlink(join(f.root,'subjects'),join(f.root,'linked-directory'));
 await inventory(f,[...f.lines,'--artifact','metrics:metrics/link=linked-directory/scenario.json']);
 refused(prepare(f),/link/);
 await inventory(f,[...f.lines,'--artifact','metrics:metrics/directory=subjects']);
 refused(prepare(f),/regular/);
 await inventory(f,[...f.lines,'--artifact','metrics:metrics/never=$(touch SHOULD-NOT-EXIST)']);
 refused(prepare(f),/No such file/);
 assert.equal(spawnSync('/usr/bin/test',['-e','SHOULD-NOT-EXIST'],{cwd:f.root}).status,1);
});

test('ambiguous selections and existing byte/catalog limits refuse rather than guess',async t=>{
 const f=await fixture(t);
 refused(prepare(f,['unknown']),/runtime manifest/);
 await inventory(f,[...f.lines,'--artifact','model_manifest:provenance/second.json=subjects/provenance/model.json']);
 refused(prepare(f),/ambiguous optional bundle role/);
 await inventory(f,[...f.lines,'--artifact','scenario:scenario.json=subjects/runtime-manifests/primary.json']);
 refused(prepare(f),/ambiguous repeated subject/);
 await inventory(f,f.lines);
 await chmod(join(f.root,'subjects/scenario.json'),0o644);refused(prepare(f),/read-only/);
 await chmod(join(f.root,'subjects/scenario.json'),0o444);
 await inventory(f,[...f.lines,...Array.from({length:65},(_,i)=>['--artifact','metrics:metrics/'+i+'=subjects/scenario.json']).flat()]);
 refused(prepare(f),/catalog limit/);
 await chmod(join(f.root,'qualification-arguments.txt'),0o600);
 await writeFile(join(f.root,'qualification-arguments.txt'),Buffer.alloc(65537,32));await chmod(join(f.root,'qualification-arguments.txt'),0o444);
 refused(prepare(f),/byte limit/);
 const large=await open(join(f.root,'large-metrics'),'wx',0o444);
 await large.truncate(16777217);await large.close();
 await inventory(f,[...f.lines,'--artifact','metrics:metrics/large=large-metrics']);
 refused(prepare(f),/input limit/);
});

test('a changed selected document after public loading is refused with no bootstrap output',async t=>{
 const f=await fixture(t);
 const script=`import importlib.util,sys,os
spec=importlib.util.spec_from_file_location("prepare_bootstrap",sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=module.load_qualification_artifact
def changed(specification,extensions):
 artifact=original(specification,extensions)
 path=specification.partition("=")[2]
 os.chmod(path,0o600);os.chmod(path,0o444)
 return artifact
module.load_qualification_artifact=changed
sys.argv=sys.argv[1:]
sys.exit(module.main())`;
 const result=spawnSync(python,['-c',script,...argv(f)],{env:environment,encoding:'utf8',timeout:30000,maxBuffer:1048576});
 refused(result,/changed during preparation/);
});

test('only the public v1/no-rule and v2/exact profile pairs are accepted as data',async t=>{
 const f=await fixture(t);
 for(const prefix of [
  ['--schema-version','qualification-bundle.v1'],
  ['--schema-version','qualification-bundle.v2','--comparison-rule','exact_assertion_outcome']
 ]){
  await inventory(f,[...prefix,...f.lines]);accepted(prepare(f));
 }
 for(const prefix of [
  ['--schema-version','qualification-bundle.v2'],
  ['--comparison-rule','exact_assertion_outcome'],
  ['--schema-version','qualification-bundle.v1','--comparison-rule','exact_assertion_outcome'],
  ['--schema-version','qualification-bundle.v3'],
  ['--schema-version','qualification-bundle.v2','--comparison-rule','arbitrary'],
  ['--schema-version','qualification-bundle.v1','--schema-version','qualification-bundle.v2','--comparison-rule','exact_assertion_outcome']
 ]){
  await inventory(f,[...prefix,...f.lines]);refused(prepare(f),/profile|inventory arguments/);
 }
});
