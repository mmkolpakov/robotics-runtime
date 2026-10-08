import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CONSUMER_SETTLEMENT_MS,waitForConsumerExit} from './consumer-settlement.mjs';
function clock(){
 let elapsed=0;
 return {now:()=>elapsed,sleep:async(ms:number)=>{elapsed+=ms},advance:(ms:number)=>{elapsed+=ms}};
}
test('two-tenant custody may settle after the former bootstrap-sized wait',async()=>{
 const c=clock();let observations=0;
 const exit=await waitForConsumerExit(async(timeoutMs:number)=>{
  observations++;assert.ok(timeoutMs>0&&timeoutMs<=5000);
  return {Running:c.now()<80000,ExitCode:0};
 },c);
 assert.equal(exit,0);assert.equal(c.now(),80000);assert.ok(observations>120);
});
test('running consumer never passes and is refused at the fixed monotonic deadline',async()=>{
 const c=clock();
 await assert.rejects(waitForConsumerExit(async()=>({Running:true,ExitCode:0}),c),/consumer active/);
 assert.equal(c.now(),CONSUMER_SETTLEMENT_MS);assert.equal(CONSUMER_SETTLEMENT_MS,270000);
});
test('settled nonzero remains nonzero and original inspection refusal remains primary',async()=>{
 const c=clock();
 assert.equal(await waitForConsumerExit(async()=>({Running:c.now()<40000,ExitCode:17}),c),17);
 const failure=new Error('native inspection refused'),d=clock();
 await assert.rejects(waitForConsumerExit(async()=>{throw failure},d),error=>error===failure);
 assert.equal(d.now(),CONSUMER_SETTLEMENT_MS);
});
test('inspection completing beyond the deadline cannot turn active work into success',async()=>{
 const c=clock();
 await assert.rejects(waitForConsumerExit(async()=>{c.advance(CONSUMER_SETTLEMENT_MS);return {Running:false,ExitCode:0}},c),/consumer active/);
});
