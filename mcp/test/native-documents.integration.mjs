import assert from 'node:assert/strict';
import {test} from 'node:test';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {chmod,mkdir,mkdtemp,readFile,readdir,rm,writeFile} from 'node:fs/promises';
import {dirname,join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
const directory=dirname(fileURLToPath(import.meta.url));
const contractsCli=process.env.MCP_TEST_CONTRACTS_CLI,harnessCli=process.env.MCP_TEST_HARNESS_CLI;
assert.ok(contractsCli&&harnessCli,'native integration requires explicitly selected installed public workers');
const example=resolve(process.env.MCP_TEST_NATIVE_EXAMPLE??join(directory,'../../packages/contracts/consumer-examples/minimal-native-archive'));
const python=join(dirname(harnessCli),'python');
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const environment={PATH:dirname(harnessCli)+':'+dirname(contractsCli)+':/usr/bin:/bin',LANG:'C.UTF-8',PYTHONDONTWRITEBYTECODE:'1'};
function invoke(command,args,status=0){
 const result=spawnSync(command,args,{env:environment,encoding:'utf8',timeout:60000,maxBuffer:1048576});
 assert.equal(result.status,status,result.stderr);return result.stdout;
}
test('installed native CLI documents cross the six readonly MCP tools without numerical conversion or execution', {timeout:120000},async t=>{
 const root=await mkdtemp(join(tmpdir(),'mcp-native-documents-'));
 t.after(()=>rm(root,{recursive:true,force:true}));
 const output=join(root,'counter');
 const produced=JSON.parse(invoke(python,[join(example,'consumer.py'),'--output',output]));
 assert.equal(produced.status,'passed');assert.equal(produced.original_inputs_unchanged,true);
 const incomplete=join(root,'incomplete');
 // Python retains producer ns integers while passing them to the public evaluator.
 invoke(python,['-c','import json,subprocess,sys; inputs=json.loads(subprocess.check_output([sys.executable,sys.argv[1],"--output",sys.argv[2],"--omit","condition"],text=True)); args=["robotics-acceptance","evaluate"]+[v for k,item in inputs.items() for v in ("--"+k.replace("_","-"),str(item))]+["--output",sys.argv[3]]; result=subprocess.run(args,capture_output=True,text=True); assert result.returncode==1,result.stderr',join(example,'producer.py'),join(incomplete,'archive'),join(incomplete,'assessment')]);
 const artifacts=join(root,'artifacts'),scratch=join(root,'scratch');
 await mkdir(artifacts,{mode:0o700});await mkdir(scratch,{mode:0o700});
 const sources={scenario:join(output,'archive/scenario.json'),runtime:join(output,'archive/runtime.json'),observation:join(output,'archive/observation.json'),result:join(output,'assessment/acceptance-result.json'),metrics:join(output,'archive/metrics.jsonl'),incomplete:join(incomplete,'assessment/acceptance-result.json')};
 const original=new Map(),entries=[];
 for(const [id,path]of Object.entries(sources)){
  const bytes=await readFile(path);original.set(id,bytes);await writeFile(join(artifacts,id+'.json'),bytes,{mode:0o444});
  entries.push({id,path:id+'.json',sha256:digest(bytes),size_bytes:bytes.length});
 }
 const observation=original.get('observation').toString();
 const sourceNs=/"start_ns":\s*(\d+)/.exec(observation)?.[1];assert.ok(sourceNs&&BigInt(sourceNs)>9007199254740991n);
 const invalid=Buffer.from(observation.replace(/"source_id":\s*"system-utc"/,'"source_id":9007199254740993'));
 assert.notEqual(invalid.toString(),observation);
 await writeFile(join(artifacts,'invalid-clock.json'),invalid,{mode:0o444});
 entries.push({id:'invalid-clock',path:'invalid-clock.json',sha256:digest(invalid),size_bytes:invalid.length});
 const config={artifactRoot:artifacts,scratchRoot:scratch,contractsCli,harnessCli,artifacts:entries,
  schemas:[{id:'native-scenario',schema:'acceptance-scenario.v2'}],bundles:[{id:'native',scenario:'scenario',runtime:'runtime'}]};
 const configPath=join(root,'bootstrap.json');await writeFile(configPath,JSON.stringify(config));
 const transport=new StdioClientTransport({command:process.execPath,args:[resolve(directory,'../bin/server.mjs'),'--config',configPath],stderr:'pipe',env:{}});
 const errors=[];transport.stderr.on('data',bytes=>errors.push(bytes.toString()));
 const client=new Client({name:'native-document-integration',version:'1.0.0'});
 t.after(async()=>{await client.close();await transport.close()});
 await client.connect(transport);
 const listed=await client.listTools();assert.deepEqual(listed.tools.map(tool=>tool.name).sort(),['describe_contract','explain_bundle','explain_result','inspect_offline_readiness','summarize_otlp','validate_documents']);
 assert.ok(listed.tools.every(tool=>tool.annotations.readOnlyHint&&!tool.annotations.destructiveHint));
 const transcript=[];
 async function call(name,args={}){
  const response=await client.callTool({name,arguments:args});assert.equal(response.content[0].type,'text');
  const value=JSON.parse(response.content[0].text);transcript.push({name,args,response});return {response,value};
 }
 const described=await call('describe_contract',{schema_id:'native-scenario'});assert.equal(described.value.ok,true,described.value.stderr);assert.match(described.value.stdout,/acceptance-scenario.v2/);
 const validated=await call('validate_documents',{artifact_ids:['scenario','runtime','observation','result']});assert.equal(validated.value.ok,true,validated.value.stdout+validated.value.stderr);
 for(const ref of validated.value.inputRefs)assert.equal(ref.sha256,digest(original.get(ref.id)));
 const explained=await call('explain_bundle',{bundle_id:'native'});assert.equal(explained.value.ok,true,explained.value.stderr);
 const explanation=JSON.parse(explained.value.stdout);assert.equal(explanation.execution.target_environment,'software');assert.equal(explanation.profile.profile_id,'org.example.native-counter');assert.equal('expected_ros_graph' in explanation,false);
 const summarized=await call('summarize_otlp',{artifact_id:'metrics'});assert.equal(summarized.value.ok,true,summarized.value.stderr);assert.equal(JSON.parse(summarized.value.stdout).sample_count,3);
 for(const [id,status]of [['result','passed'],['incomplete','incomplete']]){
  const result=await call('explain_result',{artifact_id:id});assert.equal(result.value.ok,true,result.value.stderr);assert.equal(result.response.isError,false);
  const direct=invoke(harnessCli,['why','--format','json',sources[id]]).replace(/\n$/,'');assert.equal(result.value.stdout,direct);
  const why=JSON.parse(result.value.stdout);assert.equal(why.status,status);assert.equal('forbidden_graph_violations' in why,false);
  if(id==='incomplete'){assert.ok(why.runtime_observations.some(item=>item.observation_id==='condition'&&item.status==='incomplete'));assert.ok(why.unevaluated.length)}
  assert.match(result.value.scope,/not qualification/);
 }
 const readiness=await call('inspect_offline_readiness');assert.equal(readiness.value.ok,true,readiness.value.stderr);assert.equal(JSON.parse(readiness.value.stdout).mode,'offline');
 const numericRefusal=await call('validate_documents',{artifact_ids:['invalid-clock']});assert.equal(numericRefusal.value.ok,false);assert.equal(numericRefusal.response.isError,true);
 assert.match(numericRefusal.value.stdout+numericRefusal.value.stderr,/9007199254740993/);assert.doesNotMatch(numericRefusal.value.stdout+numericRefusal.value.stderr,/9007199254740992/);
 const unknown=await call('validate_documents',{artifact_ids:['unregistered']});assert.equal(unknown.value.worker_started,false);
 const extra=await client.callTool({name:'validate_documents',arguments:{artifact_ids:['scenario'],path:'/etc/passwd',argv:['--help']}});assert.equal(extra.isError,true);
 await assert.rejects(client.callTool({name:'start_run',arguments:{}}),/not found/);
 await chmod(join(artifacts,'observation.json'),0o600);await writeFile(join(artifacts,'observation.json'),Buffer.alloc(original.get('observation').length,32));await chmod(join(artifacts,'observation.json'),0o444);
 const mutated=await call('validate_documents',{artifact_ids:['observation']});assert.equal(mutated.value.worker_started,false);assert.match(mutated.value.error,/digest/);
 for(const [id,path]of Object.entries(sources))assert.equal(digest(await readFile(path)),digest(original.get(id)));
 assert.deepEqual(await readdir(scratch),[]);assert.equal(errors.join(''),'');
 const report=process.env.MCP_TEST_REPORT_DIR;
 if(report){await mkdir(report,{recursive:true});await writeFile(join(report,'native-document-tools.json'),JSON.stringify({source_ns:sourceNs,original_inputs_unchanged:true,scope:'installed candidate CLI and readonly MCP documents; no native execution through MCP',transcript},null,2)+'\n')}
});
