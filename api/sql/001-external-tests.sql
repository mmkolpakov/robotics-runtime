CREATE SCHEMA api AUTHORIZATION api_owner;
SET ROLE api_owner;
CREATE TABLE api.tenants (id uuid PRIMARY KEY);
CREATE TABLE api.memberships (
 tenant_id uuid NOT NULL REFERENCES api.tenants(id), issuer text NOT NULL, subject text NOT NULL,
 account text NOT NULL, principal_id uuid NOT NULL,
 PRIMARY KEY (tenant_id, issuer, subject)
);
CREATE TABLE api.projects (
 tenant_id uuid NOT NULL REFERENCES api.tenants(id), id uuid NOT NULL, name text NOT NULL,
 PRIMARY KEY (tenant_id,id), UNIQUE(id)
);
CREATE TABLE api.project_memberships (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, issuer text NOT NULL, subject text NOT NULL,
 PRIMARY KEY (tenant_id,project_id,issuer,subject),
 FOREIGN KEY (tenant_id,project_id) REFERENCES api.projects(tenant_id,id),
 FOREIGN KEY (tenant_id,issuer,subject) REFERENCES api.memberships(tenant_id,issuer,subject)
);
CREATE TABLE api.branches (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, id uuid NOT NULL, name text NOT NULL,
 branch_type text NOT NULL CHECK(branch_type IN ('MAIN','CHANGE_REQUEST','RELEASE')),
 created_at timestamptz NOT NULL DEFAULT now(), created_by uuid NOT NULL,
 PRIMARY KEY(tenant_id,project_id,id), UNIQUE(tenant_id,project_id,name),
 FOREIGN KEY(tenant_id,project_id) REFERENCES api.projects(tenant_id,id)
);
CREATE TABLE api.batches (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, id uuid NOT NULL, branch_id uuid NOT NULL,
 name text NOT NULL, version text, account text NOT NULL, created_by uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), closed_at timestamptz,
 PRIMARY KEY(tenant_id,project_id,id),
 FOREIGN KEY(tenant_id,project_id,branch_id) REFERENCES api.branches(tenant_id,project_id,id)
);
CREATE TABLE api.experiences (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, id uuid NOT NULL, name text NOT NULL,
 PRIMARY KEY(tenant_id,project_id,id), UNIQUE(tenant_id,project_id,name),
 FOREIGN KEY(tenant_id,project_id) REFERENCES api.projects(tenant_id,id)
);
CREATE TABLE api.jobs (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, batch_id uuid NOT NULL, id uuid NOT NULL,
 experience_id uuid NOT NULL, name text NOT NULL, created_by uuid NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), close_status text, close_error text, closed_at timestamptz,
 CHECK(close_status IS NULL OR close_status IN ('SUCCEEDED','ERROR')),
 PRIMARY KEY(tenant_id,project_id,batch_id,id),
 FOREIGN KEY(tenant_id,project_id,batch_id) REFERENCES api.batches(tenant_id,project_id,id),
 FOREIGN KEY(tenant_id,project_id,experience_id) REFERENCES api.experiences(tenant_id,project_id,id)
);
CREATE TABLE api.uploads (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, batch_id uuid NOT NULL, job_id uuid NOT NULL,
 id uuid NOT NULL, file_name text NOT NULL, checksum text NOT NULL CHECK(checksum ~ '^[0-9a-f]{64}$'),
 size_bytes bigint NOT NULL CHECK(size_bytes >= 0 AND size_bytes <= 1073741824),
 media_type text NOT NULL, log_type text NOT NULL, object_key text NOT NULL UNIQUE,
 version_id text CHECK(version_id IS NULL OR (version_id <> '' AND version_id <> 'null')),
 retained_at timestamptz,
 PRIMARY KEY(tenant_id,project_id,batch_id,job_id,id),
 UNIQUE(tenant_id,project_id,batch_id,job_id,file_name),
 FOREIGN KEY(tenant_id,project_id,batch_id,job_id) REFERENCES api.jobs(tenant_id,project_id,batch_id,id)
);
CREATE TABLE api.upload_proofs (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, batch_id uuid NOT NULL, job_id uuid NOT NULL,
 upload_id uuid NOT NULL, role text NOT NULL, raw bytea NOT NULL, sha256 text NOT NULL,
 CHECK(role IN ('receipt','verification','statement','trust-policy','signature')),
 PRIMARY KEY(tenant_id,project_id,batch_id,job_id,upload_id,role),
 FOREIGN KEY(tenant_id,project_id,batch_id,job_id,upload_id)
 REFERENCES api.uploads(tenant_id,project_id,batch_id,job_id,id)
);
ALTER TABLE api.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY self_membership ON api.memberships FOR SELECT USING (
 issuer = current_setting('api.issuer', true) AND subject = current_setting('api.subject', true)
);
ALTER TABLE api.project_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.project_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY self_project_membership ON api.project_memberships FOR SELECT USING (
 issuer = current_setting('api.issuer', true) AND subject = current_setting('api.subject', true)
);
ALTER TABLE api.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY admitted_tenant ON api.tenants FOR SELECT USING (
 EXISTS(SELECT 1 FROM api.memberships m WHERE m.tenant_id=id)
);
ALTER TABLE api.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.projects FORCE ROW LEVEL SECURITY;
CREATE POLICY admitted_project ON api.projects FOR SELECT USING (
 EXISTS(SELECT 1 FROM api.project_memberships m WHERE m.tenant_id=projects.tenant_id AND m.project_id=projects.id)
);
DO $policies$
DECLARE relation text;
BEGIN
 FOREACH relation IN ARRAY ARRAY['branches','batches','experiences','jobs','uploads','upload_proofs'] LOOP
  EXECUTE format('ALTER TABLE api.%I ENABLE ROW LEVEL SECURITY', relation);
  EXECUTE format('ALTER TABLE api.%I FORCE ROW LEVEL SECURITY', relation);
  EXECUTE format('CREATE POLICY admitted_project ON api.%I USING
    (EXISTS(SELECT 1 FROM api.project_memberships m WHERE m.tenant_id=%I.tenant_id AND m.project_id=%I.project_id))
    WITH CHECK (EXISTS(SELECT 1 FROM api.project_memberships m WHERE m.tenant_id=%I.tenant_id AND m.project_id=%I.project_id))',
    relation,relation,relation,relation,relation);
 END LOOP;
END; $policies$;
GRANT USAGE ON SCHEMA api TO api_app;
GRANT SELECT ON api.tenants,api.memberships,api.projects,api.project_memberships,api.branches TO api_app;
GRANT SELECT,INSERT ON api.batches,api.experiences,api.jobs,api.uploads,api.upload_proofs TO api_app;
GRANT UPDATE(closed_at) ON api.batches TO api_app;
GRANT UPDATE(name) ON api.experiences TO api_app;
GRANT UPDATE(close_status,close_error,closed_at) ON api.jobs TO api_app;
GRANT UPDATE(version_id,retained_at) ON api.uploads TO api_app;
CREATE FUNCTION api.keep_object_version() RETURNS trigger LANGUAGE plpgsql AS $version$
BEGIN
 IF OLD.version_id IS NOT NULL AND NEW.version_id IS DISTINCT FROM OLD.version_id THEN
  RAISE EXCEPTION 'registered immutable object version cannot change';
 END IF;
 RETURN NEW;
END; $version$;
CREATE TRIGGER fixed_object_version BEFORE UPDATE ON api.uploads FOR EACH ROW EXECUTE FUNCTION api.keep_object_version();


RESET ROLE;
