import {readdir,readFile,mkdir,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {redactDiagnostics,publishSafeFiles,assertSafeArtifact} from './safe-diagnostics.mjs';
const suite=process.argv[2];
if(!suite||!/^[a-z0-9-]{1,80}$/.test(suite))throw new Error('owned suite required');
const artifacts=resolve(new URL('../../artifacts/',import.meta.url).pathname);
const destination=join(artifacts,'api-ci-safe',suite);
await mkdir(destination,{recursive:true});
const proofRole='(?:receipt|verification|statement|trust-policy|signature)';
const allowed=new RegExp('^(?:fixture-owner\\.json|role-report\\.json|gateway-report\\.json|sdk-report\\.json|proxy-report\\.json|cli-attempts\\.jsonl|(?:consumer|api|s3)-failure\\.log|config/(?:sdk-config\\.yml|sdk-template\\.liquid|snapshots\\.json)|(?:custody|concurrency|recovery)/[0-9a-f-]{36}/(?:payload|object\\.json|'+proofRole+')|custody/(?:custody\\.pub|signing\\.json|trusted-root\\.json|sdk-emissions-[0-9a-f-]{36}\\.jsonl|sdk-attachment\\.png|sdk-empty\\.log)|recovery/(?:before\\.json|after\\.json|before-'+proofRole+'|after-[0-9a-f-]{36}-'+proofRole+'))$');
async function walk(base,prefix=''){
 const result=[];
 for(const entry of await readdir(join(base,prefix),{withFileTypes:true})){
  const relative=prefix?prefix+'/'+entry.name:entry.name;
  if(entry.isDirectory()){if(entry.name!=='secrets')result.push(...await walk(base,relative))}
  else if(entry.isFile()&&allowed.test(relative))result.push(relative);
 }
 return result;
}
for(const entry of await readdir(artifacts,{withFileTypes:true})){
 if(!entry.isDirectory()||!/^rr-(?:sdk-api|api-pg)-[a-f0-9]{8}$/.test(entry.name))continue;
 const base=join(artifacts,entry.name);
 let marker;try{marker=JSON.parse(await readFile(join(base,'fixture-owner.json'),'utf8'))}catch(error){if(error.code==='ENOENT')continue;throw error}
 if(marker.suite!==suite)continue;
 if(marker.owner!==entry.name)throw new Error('safe closure owner mismatch');
 await publishSafeFiles(base,join(destination,entry.name),await walk(base));
}
for(const entry of await readdir(artifacts,{withFileTypes:true})){
 if(!entry.isFile()||!entry.name.startsWith('api-ci-'+suite)||!/\.(?:json|log)$/.test(entry.name))continue;
 const raw=await readFile(join(artifacts,entry.name));
 if(entry.name.endsWith('.log')){
  const temporary=join(destination,'diagnostics');await mkdir(temporary,{recursive:true});
  const safe=Buffer.from(redactDiagnostics(raw.toString('utf8')));assertSafeArtifact(safe);
  await writeFile(join(temporary,entry.name),safe);
 }else await publishSafeFiles(artifacts,join(destination,'driver'),[entry.name]);
}
