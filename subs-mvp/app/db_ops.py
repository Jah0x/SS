from __future__ import annotations

from typing import Optional
from uuid import UUID

from psycopg import errors


async def resolve_user_id(conn, login: str) -> Optional[int]:
    for column in ("email", "login", "username"):
        try:
            cur = await conn.execute(
                f"SELECT id FROM users WHERE {column} = %(login)s LIMIT 1",
                {"login": login},
            )
            row = await cur.fetchone()
            if row:
                return int(row[0])
        except errors.UndefinedColumn:
            continue
    return None


async def revoke_all_for_user(conn, user_id: int) -> None:
    await conn.execute(
        "UPDATE uid_assignments SET revoked_at = NOW() WHERE user_id = %(id)s AND revoked_at IS NULL",
        {"id": user_id},
    )
    await conn.execute(
        """
        UPDATE uids u SET status='free', updated_at=NOW()
        WHERE EXISTS (
          SELECT 1 FROM uid_assignments a
          WHERE a.uid=u.uid AND a.user_id=%(id)s AND a.revoked_at IS NOT NULL
        )
        """,
        {"id": user_id},
    )


async def allocate_specific_uid(conn, uid: UUID) -> bool:
    cur = await conn.execute(
        "UPDATE uids SET status='allocated', updated_at=NOW() WHERE uid=%(uid)s::uuid AND status='free'",
        {"uid": str(uid)},
    )
    return cur.rowcount == 1


async def allocate_any_free_uid(conn) -> Optional[UUID]:
    cur = await conn.execute(
        """
        WITH ap AS (SELECT id FROM pools WHERE is_active=TRUE LIMIT 1),
        pick AS (
          SELECT uid FROM uids
          WHERE pool=(SELECT id FROM ap) AND status='free'
          FOR UPDATE SKIP LOCKED
          LIMIT 1
        )
        UPDATE uids
           SET status='allocated', updated_at=NOW()
         WHERE uid IN (SELECT uid FROM pick)
        RETURNING uid;
        """,
    )
    row = await cur.fetchone()
    if row:
        return UUID(row[0])
    return None


async def link_assignment(conn, uid: UUID, user_id: int) -> None:
    await conn.execute(
        "INSERT INTO uid_assignments (uid, user_id) VALUES (%(uid)s, %(user_id)s)",
        {"uid": str(uid), "user_id": user_id},
    )


async def get_status_by_login(conn, login: str) -> Optional[dict]:
    user_id = await resolve_user_id(conn, login)
    if user_id is None:
        return None
    cur = await conn.execute(
        "SELECT uid, assigned_at FROM uid_assignments WHERE user_id=%(id)s AND revoked_at IS NULL",
        {"id": user_id},
    )
    row = await cur.fetchone()
    if not row:
        return {"login": login, "user_id": user_id, "active": False}
    return {
        "login": login,
        "user_id": user_id,
        "uid": row[0],
        "assigned_at": row[1],
        "active": True,
    }


async def get_status_by_uid(conn, uid: UUID) -> Optional[dict]:
    cur = await conn.execute(
        """
        SELECT u.uid, u.pool, u.status, u.updated_at, a.user_id, a.assigned_at
        FROM uids u
        LEFT JOIN uid_assignments a ON a.uid=u.uid AND a.revoked_at IS NULL
        WHERE u.uid=%(uid)s::uuid
        """,
        {"uid": str(uid)},
    )
    row = await cur.fetchone()
    if not row:
        return None
    return {
        "uid": row[0],
        "pool": row[1],
        "status": row[2],
        "updated_at": row[3],
        "user_id": row[4],
        "assigned_at": row[5],
    }
