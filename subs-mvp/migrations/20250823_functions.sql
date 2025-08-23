BEGIN;

-- resolve user by login/username/email
CREATE OR REPLACE FUNCTION subs_resolve_user_id(p_login TEXT)
RETURNS BIGINT LANGUAGE plpgsql STABLE AS $$
DECLARE v_user_id BIGINT;
BEGIN
  BEGIN EXECUTE 'SELECT id FROM users WHERE LOWER(login)=LOWER($1) LIMIT 1'
    INTO v_user_id USING p_login; EXCEPTION WHEN undefined_column THEN v_user_id := NULL; END;
  IF v_user_id IS NULL THEN
    BEGIN EXECUTE 'SELECT id FROM users WHERE LOWER(username)=LOWER($1) LIMIT 1'
      INTO v_user_id USING p_login; EXCEPTION WHEN undefined_column THEN v_user_id := NULL; END;
  END IF;
  IF v_user_id IS NULL THEN
    BEGIN EXECUTE 'SELECT id FROM users WHERE LOWER(email)=LOWER($1) LIMIT 1'
      INTO v_user_id USING p_login; EXCEPTION WHEN undefined_column THEN v_user_id := NULL; END;
  END IF;
  IF v_user_id IS NULL THEN RAISE EXCEPTION 'User with login "%" not found', p_login; END IF;
  RETURN v_user_id;
END; $$;

-- atomic allocate
CREATE OR REPLACE FUNCTION subs_assign_uid(p_user_id BIGINT)
RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE v_uid UUID;
BEGIN
  WITH ap AS (SELECT id FROM pools WHERE is_active=TRUE LIMIT 1),
  pick AS (
    SELECT uid FROM uids
    WHERE pool=(SELECT id FROM ap) AND status='free'
    FOR UPDATE SKIP LOCKED
    LIMIT 1
  )
  UPDATE uids SET status='allocated', updated_at=NOW()
  WHERE uid IN (SELECT uid FROM pick)
  RETURNING uid INTO v_uid;

  IF v_uid IS NULL THEN RAISE EXCEPTION 'No free UID in active pool'; END IF;

  INSERT INTO uid_assignments(uid, user_id) VALUES (v_uid, p_user_id);
  RETURN v_uid;
END; $$;

-- by login
CREATE OR REPLACE FUNCTION subs_assign_uid_by_login(p_login TEXT)
RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE v_user_id BIGINT; v_uid UUID;
BEGIN
  v_user_id := subs_resolve_user_id(p_login);
  v_uid := subs_assign_uid(v_user_id);
  RETURN v_uid;
END; $$;

-- revoke by login
CREATE OR REPLACE FUNCTION subs_revoke_by_login(p_login TEXT)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE v_user_id BIGINT;
BEGIN
  v_user_id := subs_resolve_user_id(p_login);
  UPDATE uid_assignments SET revoked_at=NOW()
   WHERE user_id=v_user_id AND revoked_at IS NULL;
  UPDATE uids u SET status='free', updated_at=NOW()
   WHERE EXISTS (SELECT 1 FROM uid_assignments a
                 WHERE a.uid=u.uid AND a.user_id=v_user_id AND a.revoked_at IS NOT NULL);
END; $$;

COMMIT;
