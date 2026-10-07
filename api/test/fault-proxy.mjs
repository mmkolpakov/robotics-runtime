import {createServer,request} from 'node:http';
import {writeFile} from 'node:fs/promises';
const permitted=new Set(['api:3000','s3-fixture:8333','keycloak:8080']);
const observations=[];let droppedLog=false,droppedClose=false;
createServer((incoming,outgoing)=>{
 let url;try{url=new URL(incoming.url)}catch{outgoing.writeHead(400);outgoing.end();return}
 if(!permitted.has(url.host)){observations.push({method:incoming.method,host:url.host,path:url.pathname,refused:true});outgoing.writeHead(403);outgoing.end();return}
 observations.push({method:incoming.method,host:url.host,path:url.pathname});
 const upstream=request(url,{method:incoming.method,headers:incoming.headers},response=>{
  const registration=incoming.method==='POST'&&url.host==='api:3000'&&url.pathname.endsWith('/logs')&&response.statusCode===201;
  const close=incoming.method==='POST'&&url.host==='api:3000'&&/\/jobs\/[^/]+\/close$/.test(url.pathname)&&response.statusCode===204;
  if((registration&&!droppedLog)||(close&&!droppedClose)){
   if(registration)droppedLog=true;if(close)droppedClose=true;
   response.resume();response.once('end',()=>outgoing.destroy());return;
  }
  outgoing.writeHead(response.statusCode,response.headers);response.pipe(outgoing);
 });
 upstream.on('error',()=>{if(!outgoing.headersSent)outgoing.writeHead(502);outgoing.end()});
 incoming.pipe(upstream);
}).listen(8080,'0.0.0.0');
async function save(){await writeFile('/work/proxy-report.json',JSON.stringify({permitted:[...permitted],observations,droppedLog,droppedClose},null,2)+'\n')}
setInterval(()=>{void save()},500);
for(const signal of ['SIGTERM','SIGINT'])process.once(signal,()=>{void save().finally(()=>process.exit())});
