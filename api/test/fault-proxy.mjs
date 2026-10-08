import {createServer,request} from 'node:http';
import {writeFile} from 'node:fs/promises';
const permitted=new Set(['api:3000','s3-fixture:8333','keycloak:8080']);
const observations=[];let droppedLog=false,droppedClose=false,droppedConfig=false;
createServer((incoming,outgoing)=>{
 let url;try{url=new URL(incoming.url)}catch{outgoing.writeHead(400);outgoing.end();return}
 if(!permitted.has(url.host)){observations.push({method:incoming.method,host:url.host,path:url.pathname,refused:true});outgoing.writeHead(403);outgoing.end();return}
 const observation={method:incoming.method,host:url.host,path:url.pathname};observations.push(observation);
 if(incoming.method==='POST'&&url.host==='api:3000'&&url.pathname.endsWith('/batches/light')){
  const chunks=[];let size=0;
  incoming.on('data',chunk=>{size+=chunk.length;if(size<=4096)chunks.push(chunk)});
  incoming.once('end',()=>{
   if(size>4096){observation.batchInputObservation='bounded-capture-refused';return}
   try{const body=JSON.parse(Buffer.concat(chunks).toString('utf8'));observation.metricsSetName={present:Object.hasOwn(body,'metricsSetName'),value:body.metricsSetName??null}}
   catch{observation.batchInputObservation='invalid-JSON'}
  });
 }
 const upstream=request(url,{method:incoming.method,headers:incoming.headers},response=>{
  const config=incoming.method==='POST'&&url.host==='api:3000'&&url.pathname==='/graphql'&&response.statusCode===200;
  const registration=incoming.method==='POST'&&url.host==='api:3000'&&url.pathname.endsWith('/logs')&&response.statusCode===201;
  const close=incoming.method==='POST'&&url.host==='api:3000'&&/\/jobs\/[^/]+\/close$/.test(url.pathname)&&response.statusCode===204;
  if((registration&&!droppedLog)||(close&&!droppedClose)||(config&&!droppedConfig)){
   if(registration)droppedLog=true;if(close)droppedClose=true;if(config)droppedConfig=true;
   response.resume();response.once('end',()=>outgoing.destroy());return;
  }
  outgoing.writeHead(response.statusCode,response.headers);response.pipe(outgoing);
 });
 upstream.on('error',()=>{if(!outgoing.headersSent)outgoing.writeHead(502);outgoing.end()});
 incoming.pipe(upstream);
}).listen(8080,'0.0.0.0');
async function save(){await writeFile('/work/proxy-report.json',JSON.stringify({permitted:[...permitted],observations,droppedLog,droppedClose,droppedConfig},null,2)+'\n')}
setInterval(()=>{void save()},500);
for(const signal of ['SIGTERM','SIGINT'])process.once(signal,()=>{void save().finally(()=>process.exit())});
