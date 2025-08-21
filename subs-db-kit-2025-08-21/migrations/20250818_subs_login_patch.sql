BEGIN;

CREATE TABLE IF NOT EXISTS uid_sources (
  uid         UUID PRIMARY KEY REFERENCES uids(uid) ON DELETE CASCADE,
  cm_name     TEXT NOT NULL,
  pool        TEXT NOT NULL REFERENCES pools(id) ON DELETE RESTRICT,
  last_seen   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS uid_sources_cm_idx ON uid_sources (cm_name);
CREATE INDEX IF NOT EXISTS uid_sources_pool_idx ON uid_sources (pool);

CREATE OR REPLACE FUNCTION trg_touch_last_seen() RETURNS trigger AS $$
BEGIN
  NEW.last_seen := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_uid_sources_touch ON uid_sources;
CREATE TRIGGER trg_uid_sources_touch
  BEFORE UPDATE ON uid_sources
  FOR EACH ROW EXECUTE FUNCTION trg_touch_last_seen();

CREATE OR REPLACE FUNCTION subs_resolve_user_id(p_login TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v_user_id BIGINT;
BEGIN
  BEGIN
    EXECUTE 'SELECT id FROM users WHERE LOWER(login) = LOWER($1) LIMIT 1'
    INTO v_user_id USING p_login;
  EXCEPTION WHEN undefined_column THEN
    v_user_id := NULL;
  END;

  IF v_user_id IS NULL THEN
    BEGIN
      EXECUTE 'SELECT id FROM users WHERE LOWER(username) = LOWER($1) LIMIT 1'
      INTO v_user_id USING p_login;
    EXCEPTION WHEN undefined_column THEN
      v_user_id := NULL;
    END;
  END IF;

  IF v_user_id IS NULL THEN
    BEGIN
      EXECUTE 'SELECT id FROM users WHERE LOWER(email) = LOWER($1) LIMIT 1'
      INTO v_user_id USING p_login;
    EXCEPTION WHEN undefined_column THEN
      v_user_id := NULL;
    END;
  END IF;

  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'User with login "%" not found', p_login;
  END IF;

  RETURN v_user_id;
END;
$$;

CREATE OR REPLACE FUNCTION subs_assign_uid_by_login(p_login TEXT)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  v_user_id BIGINT;
  v_uid UUID;
BEGIN
  v_user_id := subs_resolve_user_id(p_login);
  v_uid := subs_assign_uid(v_user_id);
  RETURN v_uid;
END;
$$;

CREATE OR REPLACE FUNCTION subs_revoke_by_login(p_login TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
  v_user_id BIGINT;
BEGIN
  v_user_id := subs_resolve_user_id(p_login);

  UPDATE uid_assignments
     SET revoked_at = NOW()
   WHERE user_id = v_user_id
     AND revoked_at IS NULL;

  UPDATE uids u
     SET status = 'free', updated_at = NOW()
   WHERE EXISTS (
     SELECT 1 FROM uid_assignments a
     WHERE a.uid = u.uid AND a.user_id = v_user_id AND a.revoked_at IS NOT NULL
   );
END;
$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='login') THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS users_login_lower_idx ON users (LOWER(login))';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='username') THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS users_username_lower_idx ON users (LOWER(username))';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='email') THEN
    EXECUTE 'CREATE INDEX IF NOT EXISTS users_email_lower_idx ON users (LOWER(email))';
  END IF;
END
$$;

COMMIT;
