import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..auth import auth
from ..db import pool
from .. import db_ops
from ..models import AssignReq, AssignResp, RevokeReq, StatusResp
from ..vless import build_vless

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["v1"], dependencies=[Depends(auth)])


@router.post("/assign", response_model=AssignResp)
async def assign(req: AssignReq):
    async with pool.connection() as conn:
        async with conn.transaction():
            user_id = await db_ops.resolve_user_id(conn, req.login)
            if user_id is None:
                raise HTTPException(
                    status_code=404,
                    detail={"error": {"code": "user_not_found", "message": "user not found"}},
                )
            await db_ops.revoke_all_for_user(conn, user_id)
            if req.uid:
                ok = await db_ops.allocate_specific_uid(conn, req.uid)
                if not ok:
                    raise HTTPException(
                        status_code=409,
                        detail={"error": {"code": "uid_not_free", "message": "uid not free"}},
                    )
                uid = req.uid
            else:
                uid = await db_ops.allocate_any_free_uid(conn)
                if uid is None:
                    raise HTTPException(
                        status_code=409,
                        detail={"error": {"code": "no_free_uid", "message": "no free uid"}},
                    )
            await db_ops.link_assignment(conn, uid, user_id)
            logger.info("assign login=%s uid=%s", req.login, uid)
            return AssignResp(uid=uid)


@router.post("/revoke", status_code=204)
async def revoke(req: RevokeReq):
    async with pool.connection() as conn:
        async with conn.transaction():
            user_id = await db_ops.resolve_user_id(conn, req.login)
            if user_id is None:
                raise HTTPException(
                    status_code=404,
                    detail={"error": {"code": "user_not_found", "message": "user not found"}},
                )
            await db_ops.revoke_all_for_user(conn, user_id)
            logger.info("revoke login=%s", req.login)
    return Response(status_code=204)


@router.get("/status", response_model=StatusResp)
async def status(login: Optional[str] = None, uid: Optional[UUID] = None):
    if not login and not uid:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "bad_request", "message": "login or uid required"}},
        )
    async with pool.connection() as conn:
        async with conn.transaction():
            if login:
                res = await db_ops.get_status_by_login(conn, login)
                if res is None:
                    raise HTTPException(
                        status_code=404,
                        detail={"error": {"code": "not_found", "message": "not found"}},
                    )
                return res
            else:
                res = await db_ops.get_status_by_uid(conn, uid)
                if res is None:
                    raise HTTPException(
                        status_code=404,
                        detail={"error": {"code": "not_found", "message": "not found"}},
                    )
                return res


@router.get("/sub")
async def sub(login: Optional[str] = None, uid: Optional[UUID] = None, fmt: str = "plain"):
    if fmt not in ("plain", "b64"):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "bad_request", "message": "invalid fmt"}},
        )
    if not login and not uid:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "bad_request", "message": "login or uid required"}},
        )
    async with pool.connection() as conn:
        async with conn.transaction():
            final_uid: UUID
            if login:
                res = await db_ops.get_status_by_login(conn, login)
                if res is None or not res.get("uid") or not res.get("active"):
                    raise HTTPException(
                        status_code=404,
                        detail={"error": {"code": "not_found", "message": "not found"}},
                    )
                final_uid = UUID(str(res["uid"]))
            else:
                res = await db_ops.get_status_by_uid(conn, uid)
                if res is None:
                    raise HTTPException(
                        status_code=404,
                        detail={"error": {"code": "not_found", "message": "not found"}},
                    )
                final_uid = uid
    link = build_vless(final_uid, fmt)
    return link
