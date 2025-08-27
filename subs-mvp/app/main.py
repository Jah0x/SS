import asyncio
from fastapi import FastAPI

from .db import pool
from .watcher import CMWatcher
from .routers import v1

app = FastAPI(title="Subs", version="0.1.0")
app.include_router(v1.router)

@app.on_event("startup")
async def on_startup():
    await pool.open()
    loop = asyncio.get_running_loop()
    app.state.cm_watcher = CMWatcher(loop)
    app.state._watcher_thread = app.state.cm_watcher.start_in_thread()

@app.on_event("shutdown")
async def on_shutdown():
    if getattr(app.state, "cm_watcher", None):
        app.state.cm_watcher.stop()
    await pool.close()

@app.get("/healthz")
async def healthz():
    return {"ok": True}
