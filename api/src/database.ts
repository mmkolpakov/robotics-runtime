import {Pool,type PoolClient} from 'pg';
import type {Principal} from './identity.js';
export class ApiError extends Error {constructor(readonly status:number,message:string){super(message)}}
export async function transactionClient<T>(client:PoolClient,principal:Principal,work:(client:PoolClient)=>Promise<T>):Promise<T>{
 try{
  await client.query('BEGIN');
  await client.query("SELECT set_config('api.issuer',$1,true),set_config('api.subject',$2,true),set_config('lock_timeout','30000',true)",
   [principal.issuer,principal.subject]);
  const value=await work(client);await client.query('COMMIT');return value;
 }catch(error){await client.query('ROLLBACK');throw error}
}
export async function transaction<T>(pool:Pool,principal:Principal,work:(client:PoolClient)=>Promise<T>):Promise<T>{
 const client=await pool.connect();
 try{return await transactionClient(client,principal,work)}finally{client.release()}
}
export async function project(client:PoolClient,id:string){
 const found=await client.query("SELECT p.tenant_id,p.id,m.principal_id,m.account FROM api.projects p JOIN api.memberships m ON m.tenant_id=p.tenant_id WHERE p.id=$1",[id]);
 if(found.rows.length!==1)throw new ApiError(404,'project not found');
 return found.rows[0] as {tenant_id:string;id:string;principal_id:string;account:string};
}
export async function verifyApplicationRole(pool:Pool){
 const state=await pool.query("SELECT r.rolsuper,r.rolbypassrls,r.rolcreaterole,EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='api' AND (pg_has_role(current_user,c.relowner,'USAGE') OR pg_has_role(current_user,c.relowner,'SET') OR pg_has_role(current_user,c.relowner,'MEMBER'))) AS owns_tables,EXISTS(SELECT 1 FROM pg_roles elevated WHERE (elevated.rolsuper OR elevated.rolbypassrls OR elevated.rolcreaterole) AND (pg_has_role(current_user,elevated.oid,'USAGE') OR pg_has_role(current_user,elevated.oid,'SET'))) AS privileged_role FROM pg_roles r WHERE r.rolname=current_user");
 const actual=state.rows[0];if(!actual||actual.rolsuper||actual.rolbypassrls||actual.rolcreaterole||actual.owns_tables||actual.privileged_role)throw new Error('application role must not own tables or bypass RLS');
 const tables=await pool.query("SELECT count(*)::int AS total,bool_and(c.relrowsecurity AND c.relforcerowsecurity) AS protected FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='api' AND c.relkind='r'");
 if(tables.rows[0].total!==10||tables.rows[0].protected!==true)throw new Error('all metadata tables require forced RLS');
}
