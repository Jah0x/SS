from typing import Iterable, Tuple
from uuid import UUID
from psycopg_pool import AsyncConnectionPool

from .config import settings

# Пул соединений открывается вручную в событии старта приложения
pool = AsyncConnectionPool(
    conninfo=settings.DB_DSN,
    min_size=1,
    max_size=10,
    open=False,
)

async def upsert_uids_from_cm(cm_name: str, pool_id: str, uids: Iterable[UUID]) -> Tuple[int, int]:
    """Insert new UIDs as 'free' and update uid_sources for all.

    Returns (inserted_new, total_seen).
    """
    ulist = list({str(u) for u in uids})
    if not ulist:
        return 0, 0
    inserted = 0
    async with pool.connection() as conn:
        async with conn.transaction():
            # Track newly inserted count via RETURNING
            res = await conn.execute(
                """
                WITH src AS (
                  SELECT uid::uuid AS u FROM UNNEST(%(uids)s::text[]) AS t(uid)
                ), ins AS (
                  INSERT INTO uids (uid, pool, status)
                  SELECT u, %(pool)s, 'free' FROM src
                  ON CONFLICT (uid) DO NOTHING
                  RETURNING 1
                )
                SELECT COUNT(*) FROM ins;
                """,
                {"pool": pool_id, "uids": ulist},
            )
            row = await res.fetchone()
            inserted = int(row[0]) if row else 0

            await conn.execute(
                """
                INSERT INTO uid_sources (uid, cm_name, pool, last_seen)
                SELECT uid::uuid, %(cm)s, %(pool)s, NOW()
                FROM UNNEST(%(uids)s::text[]) AS t(uid)
                ON CONFLICT (uid) DO UPDATE
                   SET cm_name = EXCLUDED.cm_name,
                       pool    = EXCLUDED.pool,
                       last_seen = NOW();
                """,
                {"cm": cm_name, "pool": pool_id, "uids": ulist},
            )
    return inserted, len(ulist)

async def assign_uid_by_login(login: str) -> str:
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT subs_assign_uid_by_login(%(login)s)", {"login": login}
            )
            row = await cur.fetchone()
            if not row or not row[0]:
                raise ValueError("No free UID available")
            return str(row[0])

async def revoke_by_login(login: str) -> None:
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(
                "SELECT subs_revoke_by_login(%(login)s)", {"login": login}
            )

async def uid_status(uid: UUID) -> tuple[str, str]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            SELECT u.status, u.pool
            FROM uids u
            WHERE u.uid = %(uid)s::uuid
            """,
            {"uid": str(uid)},
        )
        row = await cur.fetchone()
        if not row:
            raise LookupError("UID not found")
        return row[0], row[1]
