BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS pools (
  id         TEXT PRIMARY KEY,
  is_active  BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS pools_one_active_uq
  ON pools ((CASE WHEN is_active THEN 1 END))
  WHERE is_active;

CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pools_updated_at ON pools;
CREATE TRIGGER trg_pools_updated_at
  BEFORE UPDATE ON pools
  FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

INSERT INTO pools (id, is_active) VALUES
  ('A', TRUE)
ON CONFLICT (id) DO UPDATE
  SET is_active = EXCLUDED.is_active
WHERE pools.is_active IS DISTINCT FROM EXCLUDED.is_active;

INSERT INTO pools (id, is_active) VALUES
  ('B', FALSE)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS uids (
  uid        UUID PRIMARY KEY,
  pool       TEXT NOT NULL REFERENCES pools(id) ON DELETE RESTRICT,
  status     TEXT NOT NULL CHECK (status IN ('free','allocated','reserved','banned')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS uids_pool_status_idx ON uids (pool, status);

DROP TRIGGER IF EXISTS trg_uids_updated_at ON uids;
CREATE TRIGGER trg_uids_updated_at
  BEFORE UPDATE ON uids
  FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE TABLE IF NOT EXISTS uid_assignments (
  id              BIGSERIAL PRIMARY KEY,
  uid             UUID    NOT NULL REFERENCES uids(uid) ON DELETE RESTRICT,
  user_id         BIGINT  NOT NULL,
  subscription_id BIGINT  NULL,
  assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at      TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uid_assignments_uid_active_uq
  ON uid_assignments(uid)
  WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS configmap_sync_state (
  name             TEXT PRIMARY KEY,
  resource_version TEXT,
  checksum         TEXT,
  last_synced_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_name = 'users'
  ) THEN
    BEGIN
      ALTER TABLE uid_assignments
        ADD CONSTRAINT uid_assignments_user_fk
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'FK to users(id) not added (type mismatch or other): %', SQLERRM;
    END;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_name = 'subscriptions'
  ) THEN
    BEGIN
      ALTER TABLE uid_assignments
        ADD CONSTRAINT uid_assignments_subscription_fk
        FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL;
    EXCEPTION WHEN others THEN
      RAISE NOTICE 'FK to subscriptions(id) not added: %', SQLERRM;
    END;
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION subs_assign_uid(p_user_id BIGINT)
RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE
  v_uid UUID;
BEGIN
  WITH active_pool AS (
    SELECT id FROM pools WHERE is_active = TRUE LIMIT 1
  ),
  picked AS (
    SELECT uid
    FROM uids
    WHERE pool = (SELECT id FROM active_pool)
      AND status = 'free'
    FOR UPDATE SKIP LOCKED
    LIMIT 1
  )
  UPDATE uids
    SET status = 'allocated', updated_at = NOW()
    WHERE uid IN (SELECT uid FROM picked)
    RETURNING uid INTO v_uid;

  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'No free UID in active pool';
  END IF;

  INSERT INTO uid_assignments (uid, user_id)
  VALUES (v_uid, p_user_id);

  RETURN v_uid;
END;
$$;

COMMIT;
