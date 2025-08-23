BEGIN;

CREATE TABLE IF NOT EXISTS pools (
  id TEXT PRIMARY KEY,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uids (
  uid UUID PRIMARY KEY,
  pool TEXT NOT NULL REFERENCES pools(id),
  status TEXT NOT NULL CHECK (status IN ('free','allocated')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uid_assignments (
  uid UUID NOT NULL REFERENCES uids(uid),
  user_id BIGINT NOT NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ,
  PRIMARY KEY (uid, user_id)
);

CREATE TABLE IF NOT EXISTS uid_sources (
  uid UUID PRIMARY KEY,
  cm_name TEXT NOT NULL,
  pool TEXT NOT NULL,
  last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS configmap_sync_state (
  cm_name TEXT PRIMARY KEY,
  last_resource_version TEXT
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS uids_set_updated_at ON uids;
CREATE TRIGGER uids_set_updated_at
BEFORE UPDATE ON uids
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_uids_pool_status ON uids(pool, status);
CREATE INDEX IF NOT EXISTS idx_uid_assignments_user_id ON uid_assignments(user_id);

COMMIT;
