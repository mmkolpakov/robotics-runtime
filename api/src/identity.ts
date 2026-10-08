import {createRemoteJWKSet,jwtVerify} from 'jose';
export interface Principal {issuer:string;subject:string}
export interface IdentityConfiguration {issuer:string;audience:string;jwksUrl:string;requiredRole:string}
export function tokenVerifier(configuration:IdentityConfiguration) {
 const jwks=createRemoteJWKSet(new URL(configuration.jwksUrl),{timeoutDuration:3000});
 return async(authorization:string|undefined):Promise<Principal>=>{
  if(!authorization?.startsWith('Bearer ')||authorization.length>16384)throw new Error('bearer token required');
  const {payload}=await jwtVerify(authorization.slice(7),jwks,{issuer:configuration.issuer,audience:configuration.audience,
   algorithms:['RS256'],requiredClaims:['sub','exp'],typ:'JWT'});
  if(typeof payload.sub!=='string'||!payload.sub||payload.sub.length>512)throw new Error('invalid subject');
  const access=payload.resource_access as Record<string,{roles?:unknown}>|undefined;
  const roles=access?.[configuration.audience]?.roles;
  if(!Array.isArray(roles)||!roles.includes(configuration.requiredRole))throw new Error('required role absent');
  return {issuer:configuration.issuer,subject:payload.sub};
 };
}
