import {writeFile,mkdir,readFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';

import {redactDiagnostics,assertSafeArtifact} from '../src/diagnostics.mjs';
export {redactDiagnostics,assertSafeArtifact};
export async function retainDiagnostic(directory,name,raw,privateValues=[]){
 if(!['consumer-failure.log','api-failure.log'].includes(name))throw new Error('fixed diagnostic name required');
 const safe=Buffer.from(redactDiagnostics(raw,privateValues));assertSafeArtifact(safe,privateValues);
 await writeFile(join(directory,name),safe);
}
export async function publishSafeFiles(source,destination,files,privateValues=[]){
 const base=resolve(source),target=resolve(destination),manifest=[];
 const checked=[];
 for(const name of files){
  const from=resolve(base,name),to=resolve(target,name);
  if(!from.startsWith(base+'/')||!to.startsWith(target+'/'))throw new Error('safe closure path refused');
  const raw=await readFile(from);assertSafeArtifact(raw,privateValues);checked.push({name,to,raw});
 }
 for(const {name,to,raw}of checked){await mkdir(resolve(to,'..'),{recursive:true});await writeFile(to,raw);manifest.push({path:name,size:raw.length,sha256:createHash('sha256').update(raw).digest('hex')})}
 await mkdir(target,{recursive:true});await writeFile(join(target,'safe-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
}
