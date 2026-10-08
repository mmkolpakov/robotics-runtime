SET ROLE api_owner;
CREATE TABLE api.config_snapshots (
 tenant_id uuid NOT NULL, project_id uuid NOT NULL, branch_id uuid NOT NULL, id uuid NOT NULL,
 config bytea NOT NULL CHECK(octet_length(config)<=262144),
 config_sha256 text NOT NULL CHECK(config_sha256 ~ '^[0-9a-f]{64}$'),
 template_files jsonb NOT NULL CHECK(jsonb_typeof(template_files)='array' AND jsonb_array_length(template_files)<=32),
 snapshot_sha256 text NOT NULL CHECK(snapshot_sha256 ~ '^[0-9a-f]{64}$'),
 created_by uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,project_id,branch_id,id), UNIQUE(tenant_id,project_id,branch_id,snapshot_sha256),
 FOREIGN KEY(tenant_id,project_id,branch_id) REFERENCES api.branches(tenant_id,project_id,id)
);
ALTER TABLE api.config_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE api.config_snapshots FORCE ROW LEVEL SECURITY;
CREATE POLICY admitted_project ON api.config_snapshots USING (
 EXISTS(SELECT 1 FROM api.project_memberships m WHERE m.tenant_id=config_snapshots.tenant_id AND m.project_id=config_snapshots.project_id)
) WITH CHECK (
 EXISTS(SELECT 1 FROM api.project_memberships m WHERE m.tenant_id=config_snapshots.tenant_id AND m.project_id=config_snapshots.project_id)
);
ALTER TABLE api.branches ADD COLUMN config_snapshot_id uuid;
ALTER TABLE api.branches ADD FOREIGN KEY(tenant_id,project_id,id,config_snapshot_id) REFERENCES api.config_snapshots(tenant_id,project_id,branch_id,id);
ALTER TABLE api.batches ADD COLUMN config_snapshot_id uuid;
ALTER TABLE api.batches ADD FOREIGN KEY(tenant_id,project_id,branch_id,config_snapshot_id) REFERENCES api.config_snapshots(tenant_id,project_id,branch_id,id);
GRANT SELECT,INSERT ON api.config_snapshots TO api_app;
GRANT UPDATE(config_snapshot_id) ON api.branches TO api_app;
RESET ROLE;
