import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {join,resolve} from 'node:path';
import {randomUUID} from 'node:crypto';
import {tmpdir} from 'node:os';

for(const mode of ['listing-refusal','listing-timeout','foreign-label']){
 test('driver cleanup refuses unverified resources: '+mode,async()=>{
  const work=await mkdtemp(join(tmpdir(),'api-cleanup-')),suite='rr-api-cleanup-'+randomUUID();
  const root=resolve(process.cwd(),'..'),report=join(root,'artifacts','api-ci-'+suite+'.json');
  const id='a'.repeat(64);
  const fake=mode==='listing-refusal'?'exit 71\n':mode==='listing-timeout'?'sleep 3\nexit 0\n':[
   'if [ "$1" = ps ]; then printf "%s\\n" "'+id+'"; exit 0; fi',
   'if [ "$1" = inspect ]; then printf "%s\\n" "'+id+' foreign-suite"; exit 0; fi',
   'if [ "$1" = volume ] || [ "$1" = network ]; then exit 0; fi',
   'if [ "$1" = rm ]; then printf "foreign removal attempted\\n" >&2; exit 72; fi',
   'exit 73',
  ].join('\n');
  try{
   await writeFile(join(work,'docker'),'#!/bin/sh\n'+fake,{mode:0o700});
   const result=spawnSync('bash',[join(root,'api/test/run-fixture.sh'),'--cleanup-only'],{
    cwd:root,env:{...process.env,PATH:work+':'+process.env.PATH,API_FIXTURE_ENGINE:'docker',
     API_FIXTURE_SUITE:suite,API_FIXTURE_CLEANUP_TIMEOUT:'1'},encoding:'utf8',timeout:10000});
   assert.equal(result.status,1);
   const value=JSON.parse(await readFile(report,'utf8'));
   assert.equal(value.originalExitCode,0);
   assert.equal(value.cleanupFailed,true);
   assert.doesNotMatch(result.stderr,/foreign removal attempted/);
  }finally{await rm(work,{recursive:true,force:true});await rm(report,{force:true})}
 });
}
