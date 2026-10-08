import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer,type Server} from 'node:http';
import {once} from 'node:events';
import {ownedLoopbackEndpoint} from './owned-loopback.mjs';
const expected={id:'a'.repeat(64),owner:'fixture-owner',suite:'fixture-suite',
 networks:[{name:'fixture-internal',id:'b'.repeat(64)},{name:'fixture-bootstrap',id:'c'.repeat(64)}]};
function detail(port:number){
 return {Id:expected.id,Config:{Labels:{'org.robotics.runtime.fixture-owner':expected.owner,'org.robotics.runtime.fixture-suite':expected.suite}},
  NetworkSettings:{Networks:Object.fromEntries(expected.networks.map(n=>[n.name,{NetworkID:n.id}])),
   Ports:{'3000/tcp':[{HostIp:'127.0.0.1',HostPort:String(port)}]}},
  State:{Status:'running',Running:true,ExitCode:0,OOMKilled:false,StartedAt:'start',FinishedAt:''}};
}
async function close(server:Server){await new Promise<void>((resolve,reject)=>server.close(error=>error?reject(error):resolve()))}
test('a restarted fixture uses its new ephemeral endpoint after the old listener closes',async()=>{
 const old=createServer((request,response)=>response.end('old')),fresh=createServer((request,response)=>response.end('fresh'));
 old.listen(0,'127.0.0.1');fresh.listen(0,'127.0.0.1');
 await Promise.all([once(old,'listening'),once(fresh,'listening')]);
 try{
  const oldPort=(old.address() as {port:number}).port,newPort=(fresh.address() as {port:number}).port;
  assert.notEqual(oldPort,newPort);
  const before=ownedLoopbackEndpoint(detail(oldPort),expected),after=ownedLoopbackEndpoint(detail(newPort),expected);
  assert.equal(before.id,after.id);assert.notEqual(before.url,after.url);
  await close(old);
  await assert.rejects(fetch(before.url,{signal:AbortSignal.timeout(1000)}));
  const response=await fetch(after.url,{signal:AbortSignal.timeout(1000)});
  assert.equal(response.status,200);assert.equal(await response.text(),'fresh');
 }finally{if(old.listening)await close(old);if(fresh.listening)await close(fresh)}
});
test('foreign identity, owner, suite, network or non-loopback binding refuses endpoint discovery',()=>{
 for(const mutate of [
  (d:any)=>{d.Id='d'.repeat(64)},
  (d:any)=>{d.Config.Labels['org.robotics.runtime.fixture-owner']='foreign'},
  (d:any)=>{d.Config.Labels['org.robotics.runtime.fixture-suite']='foreign'},
  (d:any)=>{d.NetworkSettings.Networks['fixture-bootstrap'].NetworkID='d'.repeat(64)},
  (d:any)=>{d.NetworkSettings.Networks.foreign={NetworkID:'d'.repeat(64)}},
  (d:any)=>{d.NetworkSettings.Ports['3000/tcp'][0].HostIp='0.0.0.0'},
  (d:any)=>{d.NetworkSettings.Ports['3000/tcp'][0].HostIp='::'},
  (d:any)=>{d.NetworkSettings.Ports['3000/tcp'].push({HostIp:'127.0.0.1',HostPort:'12345'})},
  (d:any)=>{d.State.Running=false},
 ]){
  const current=detail(12345);mutate(current);assert.throws(()=>ownedLoopbackEndpoint(current,expected));
 }
});
