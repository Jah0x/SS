import pytest
from app.db import pool

AUTH = {"Authorization": "Bearer dummy"}


@pytest.mark.asyncio
async def test_assign_revoke_flow(client):
    # 401 without token
    resp = await client.post("/v1/assign", json={"login": "user@example.com"})
    assert resp.status_code == 401

    # assign
    resp = await client.post("/v1/assign", json={"login": "user@example.com"}, headers=AUTH)
    assert resp.status_code == 200
    uid = resp.json()["uid"]

    # check DB
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT status FROM uids WHERE uid=%(u)s", {"u": uid})
        assert (await cur.fetchone())[0] == "allocated"
        cur = await conn.execute(
            "SELECT user_id FROM uid_assignments WHERE uid=%(u)s AND revoked_at IS NULL",
            {"u": uid},
        )
        assert (await cur.fetchone())[0] == 1

    # status by login
    resp = await client.get("/v1/status", params={"login": "user@example.com"}, headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["uid"] == uid
    assert data["active"] is True

    # sub link
    resp = await client.get(
        "/v1/sub", params={"login": "user@example.com", "fmt": "plain"}, headers=AUTH
    )
    assert resp.status_code == 200
    assert resp.text.startswith("vless://")

    # uid not free
    resp = await client.post(
        "/v1/assign", json={"login": "user2@example.com", "uid": uid}, headers=AUTH
    )
    assert resp.status_code == 409

    # no free uid
    resp = await client.post(
        "/v1/assign", json={"login": "user2@example.com"}, headers=AUTH
    )
    assert resp.status_code == 409

    # revoke
    resp = await client.post("/v1/revoke", json={"login": "user@example.com"}, headers=AUTH)
    assert resp.status_code == 204

    async with pool.connection() as conn:
        cur = await conn.execute("SELECT status FROM uids WHERE uid=%(u)s", {"u": uid})
        assert (await cur.fetchone())[0] == "free"
        cur = await conn.execute("SELECT revoked_at FROM uid_assignments WHERE uid=%(u)s", {"u": uid})
        assert (await cur.fetchone())[0] is not None
