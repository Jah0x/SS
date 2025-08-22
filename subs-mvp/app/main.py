import asyncio
from fastapi import FastAPI, Depends, Header, HTTPException, status
from uuid import UUID

from .config import settings
from .db import init_db_pool, close_db_pool, assign_uid_by_login, revoke_by_login, uid_status
from .models import AssignRequest, RevokeRequest, UIDStatus, AssignResponse
from .watcher import CMWatcher

app = FastAPI(title="Subs", version="0.1.0")

async def require_internal(x_internal_token: str | None = Header(default=None)):
    if not x_internal_token or x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

@app.on_event("startup")
async def on_startup():
    await init_db_pool()
    loop = asyncio.get_running_loop()
    app.state.cm_watcher = CMWatcher(loop)
    app.state._watcher_thread = app.state.cm_watcher.start_in_thread()

@app.on_event("shutdown")
async def on_shutdown():
    if getattr(app.state, "cm_watcher", None):
        app.state.cm_watcher.stop()
    await close_db_pool()

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/v1/assign", response_model=AssignResponse, dependencies=[Depends(require_internal)])
async def assign(req: AssignRequest):
    uid = await assign_uid_by_login(req.login)
    return AssignResponse(uid=UUID(uid))

@app.post("/v1/revoke", dependencies=[Depends(require_internal)])
async def revoke(req: RevokeRequest):
    if not req.login and not req.uid:
        raise HTTPException(400, detail="login or uid is required")
    if req.login:
        await revoke_by_login(req.login)
    else:
        raise HTTPException(400, detail="revoke by uid not implemented; use login")
    return {"ok": True}

@app.get("/v1/uid/{uid}", response_model=UIDStatus, dependencies=[Depends(require_internal)])
async def get_uid(uid: UUID):
    status_, pool_ = await uid_status(uid)
    return UIDStatus(uid=uid, status=status_, pool=pool_)
