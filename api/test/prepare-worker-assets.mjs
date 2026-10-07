import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join,isAbsolute} from 'node:path';
const root=resolve(new URL('../../',import.meta.url).pathname),lock=JSON.parse(await readFile(join(root,'api/test/upstream-lock.json'),'utf8'));
const destination=join(root,'artifacts/worker-assets');await mkdir(destination,{recursive:true});
async function fixedAsset(name,bytes,sha256,mode){
 const path=join(destination,name);
 try{const existing=await readFile(path);if(createHash('sha256').update(existing).digest('hex')!==sha256)throw new Error('existing asset differs');return}
 catch(error){if(error.code!=='ENOENT')throw error}
 await writeFile(path,bytes,{mode,flag:'wx'});
}
for(const [name,sha256]of Object.entries(lock.retention.files)){
 const response=await fetch('https://raw.githubusercontent.com/mmkolpakov/robotics-runtime-infra/'+lock.retention.source+'/docker/evidence-sink/'+name);
 if(!response.ok)throw new Error('retention asset unavailable');
 const bytes=Buffer.from(await response.arrayBuffer());
 if(createHash('sha256').update(bytes).digest('hex')!==sha256)throw new Error('retention executable identity differs');
 await fixedAsset(name,bytes,sha256,0o444);
}
const initSource=process.argv[2];
if(!initSource||!isAbsolute(initSource))throw new Error('provide the existing project catatonit absolute path');
const initBytes=await readFile(initSource);
if(createHash('sha256').update(initBytes).digest('hex')!==lock.init.sha256)throw new Error('stock catatonit identity differs');
await fixedAsset('catatonit',initBytes,lock.init.sha256,0o555);
console.log('Pinned existing retention executables and stock catatonit prepared');
