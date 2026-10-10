SET ROLE api_owner;
ALTER TABLE api.batches
 ADD COLUMN request_key text,
 ADD COLUMN request_fingerprint text,
 ADD CHECK ((request_key IS NULL AND request_fingerprint IS NULL) OR
  (request_key IS NOT NULL AND octet_length(request_key) BETWEEN 1 AND 256 AND
   request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$'));
CREATE UNIQUE INDEX batch_creation_key ON api.batches(tenant_id,project_id,created_by,request_key)
 WHERE request_key IS NOT NULL;
ALTER TABLE api.jobs
 ADD COLUMN request_key text,
 ADD COLUMN request_fingerprint text,
 ADD CHECK ((request_key IS NULL AND request_fingerprint IS NULL) OR
  (request_key IS NOT NULL AND octet_length(request_key) BETWEEN 1 AND 256 AND
   request_fingerprint IS NOT NULL AND request_fingerprint ~ '^[0-9a-f]{64}$'));
CREATE UNIQUE INDEX job_creation_key ON api.jobs(tenant_id,project_id,batch_id,created_by,request_key)
 WHERE request_key IS NOT NULL;
RESET ROLE;
