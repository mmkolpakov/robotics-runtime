import {createHash} from 'node:crypto';
import {parseItem} from 'structured-headers';
import {ApiError} from './database.js';
export function creationKey(value:string|string[]|undefined):string|undefined {
 if(value===undefined)return undefined;
 try{
  if(typeof value!=='string'||value.length>1024)throw new Error('header bound');
  const [key,parameters]=parseItem(value);
  if(typeof key!=='string'||parameters.size!==0||key.length<1||key.length>256)throw new Error('key shape');
  return key;
 }catch{throw new ApiError(400,'Idempotency-Key requires one quoted string of 1 to 256 ASCII characters without parameters')}
}
export function creationFingerprint(values:readonly (string|null)[]):string {
 return createHash('sha256').update(JSON.stringify(values)).digest('hex');
}
