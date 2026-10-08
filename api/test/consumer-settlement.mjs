import {setTimeout as pause} from 'node:timers/promises';
// Fixed positive fixture: two server close budgets plus control-call allowance.
// This is not the SDK's worst-case retry duration or a performance guarantee.
export const CONSUMER_SETTLEMENT_MS=2*120000+30000;
/**
 * @param {(timeoutMs:number)=>({Running:boolean,ExitCode:number}|Promise<{Running:boolean,ExitCode:number}>)} inspect
 * @param {{now?:()=>number,sleep?:(ms:number)=>Promise<void>}} options
 */
export async function waitForConsumerExit(inspect,{now=()=>performance.now(),sleep=pause}={}){
 const deadline=now()+CONSUMER_SETTLEMENT_MS;
 let last=new Error('consumer active');
 while(now()<deadline){
  try{
   const remainingBefore=deadline-now();if(remainingBefore<=0)break;
   const state=await inspect(Math.min(5000,Math.ceil(remainingBefore)));
   if(now()>=deadline)break;
   if(!state.Running)return state.ExitCode;
   last=new Error('consumer active');
  }catch(error){last=error}
  const remaining=deadline-now();
  if(remaining>0)await sleep(Math.min(250,remaining));
 }
 throw last;
}
