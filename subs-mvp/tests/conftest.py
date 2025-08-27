import os

os.environ.setdefault("DB_DSN", "postgresql://postgres:postgres@localhost:5432/postgres")
os.environ.setdefault("SUBS_INTERNAL_TOKEN", "dummy")
os.environ.setdefault("SUBS_DOMAIN", "test.local")
os.environ.setdefault("XRAY_PORT", "443")
os.environ.setdefault("XRAY_FLOW", "xtls-rprx-vision")

import pytest
import pytest_asyncio
from httpx import AsyncClient

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app import main as app_main
from app.db import pool


class DummyWatcher:
    def __init__(self, loop):
        pass

    def start_in_thread(self):
        return None

    def stop(self):
        pass


app_main.CMWatcher = DummyWatcher
app = app_main.app


@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    await pool.open()
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                CREATE TABLE users (
                    id serial PRIMARY KEY,
                    email text,
                    login text,
                    username text
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE pools (
                    id text PRIMARY KEY,
                    is_active boolean NOT NULL
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE uids (
                    uid uuid PRIMARY KEY,
                    pool text REFERENCES pools(id),
                    status text NOT NULL,
                    updated_at timestamptz DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE uid_assignments (
                    uid uuid REFERENCES uids(uid),
                    user_id integer REFERENCES users(id),
                    assigned_at timestamptz DEFAULT NOW(),
                    revoked_at timestamptz
                );
                """
            )
            await conn.execute("INSERT INTO pools (id, is_active) VALUES ('A', TRUE);")
            await conn.execute("INSERT INTO users (id, email) VALUES (1, 'user@example.com');")
            await conn.execute("INSERT INTO users (id, email) VALUES (2, 'user2@example.com');")
            await conn.execute(
                """
                INSERT INTO uids (uid, pool, status)
                VALUES ('11111111-1111-1111-1111-111111111111', 'A', 'free');
                """
            )
    yield
    await pool.close()
