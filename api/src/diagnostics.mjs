export function redactDiagnostics(raw,privateValues=[]){
 const redactText=text=>{
 let safe=text;
 for(const value of privateValues)if(value.length>=8)safe=safe.split(value).join('[redacted]');
 safe=safe.replace(/\b(?:https?|postgres(?:ql)?|s3):\/\/[^\s"'<>]+/gi,text=>{
  try{const url=new URL(text);url.username='';url.password='';url.search=url.search?'?[redacted-query]':'';return url.toString()}
  catch{return '[redacted-url]'}
 });
 safe=safe.replace(/(\bauthorization["']?\s*[:=]\s*["']?)[^\r\n]*/gi,'$1[redacted]');
 safe=safe.replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi,'Bearer [redacted]');
 safe=safe.replace(/\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g,'[redacted-jwt]');
 safe=safe.replace(/((?:client_secret|access_token|aws_secret_access_key|aws_access_key_id|aws_session_token|cosign_password|password)["']?\s*[:=]\s*["']?)[^\s"',;}]+/gi,'$1[redacted]');
 return safe;
 };
 const value=v=>typeof v==='string'?redactText(v):Array.isArray(v)?v.map(value):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([key,item])=>[key,value(item)])):v;
 const safe=raw.split('\n').map(line=>{try{return JSON.stringify(value(JSON.parse(line)))}catch{return redactText(line)}}).join('\n');
 return Buffer.from(safe).subarray(-65536).toString('utf8');
}
export function assertSafeArtifact(raw,privateValues=[]){
 const text=raw.toString('utf8');
 if(privateValues.some(value=>value.length>=8&&text.includes(value))||
  /\bBearer\s+(?!\[redacted\])[A-Za-z0-9._~+/=-]+|\beyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b|X-Amz-(?:Signature|Credential|Security-Token)=|(?:client_secret|access_token)=(?!\[redacted\])/i.test(text))
  throw new Error('artifact contains diagnostic authority; public retention refused');
}
