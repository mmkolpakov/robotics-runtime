import {readFile} from 'node:fs/promises';
import {Pool} from 'pg';
import {createHost,Jobs} from '@robotics-runtime/host';
import {createApi} from './app.js';
import {Domain} from './domain.js';
import {verifyApplicationRole} from './database.js';
import {UploadStorage,EXISTING_ARTIFACT_MAX_BYTES} from './uploads.js';
import {Retention} from './retention.js';
function configured(name:string){const value=process.env[name];if(!value)throw new Error('required bootstrap setting '+name);return value}
if(process.versions.node!=='24.21.0')throw new Error('pinned Node24.21.0 required');
const databaseUrl=(await readFile('/run/secrets/api-database-url','utf8')).trim();
const pool=new Pool({connectionString:databaseUrl,max:8,connectionTimeoutMillis:5000});
await verifyApplicationRole(pool);
const maximum=Number(process.env.EVIDENCE_MAX_ARTIFACT_BYTES??EXISTING_ARTIFACT_MAX_BYTES);
const endpoint=configured('API_S3_ENDPOINT'),region=configured('API_S3_REGION'),bucket=configured('API_S3_BUCKET');
const storage=new UploadStorage(bucket,endpoint,region,maximum);
await storage.ready();
const ctx=await createHost({baseDirectory:'/opt/api',console:false});
await ctx.plugin(Jobs,{timeoutMs:45000,maxBufferBytes:1048576}).await();
const environment={PATH:'/opt/venv/bin:/usr/local/bin:/usr/bin:/bin',HOME:'/home/evidence',
 AWS_SHARED_CREDENTIALS_FILE:'/run/secrets/s3-credentials',AWS_CONFIG_FILE:'/run/secrets/s3-config',
 AWS_DEFAULT_REGION:region,AWS_REGION:region,AWS_ENDPOINT_URL:endpoint,AWS_EC2_METADATA_DISABLED:'true',AWS_PAGER:'',AWS_CLI_AUTO_PROMPT:'off',
 EVIDENCE_MAX_ARTIFACT_BYTES:String(maximum),COSIGN_PASSWORD:(await readFile('/run/secrets/custody-password','utf8')).trim()};
const retention=new Retention(ctx.jobs,{root:'/work/api-custody',bucket,maximumBytes:maximum,environment,
 keyPath:'/run/secrets/custody.key',publicKeyPath:'/run/secrets/custody.pub',
 signingConfiguration:'/run/secrets/signing.json',trustedRoot:'/run/secrets/trusted-root.json'});
const domain=new Domain(pool,storage,retention);
const api=createApi(domain,{issuer:configured('API_OIDC_ISSUER'),audience:configured('API_OIDC_AUDIENCE'),
 jwksUrl:configured('API_OIDC_JWKS'),requiredRole:'sdk-write'});
api.addHook('onClose',async()=>{storage.close();await ctx.fiber.dispose();await pool.end()});
await api.listen({host:'0.0.0.0',port:3000});
for(const signal of ['SIGTERM','SIGINT'] as const)process.once(signal,()=>{void api.close()});
