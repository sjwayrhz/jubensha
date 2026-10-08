import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.v1.router import router
from .core.config import settings
from .db.session import check_connection

log = logging.getLogger("jubensha")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        check_connection()
        log.info("数据库连接正常")
    except Exception as e:
        # 一期允许降级启动：DB 未配置/连不上时应用不崩，接口访问时再报错
        log.warning("数据库连接失败，降级启动（DB 相关接口将报错）: %s", e)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)


@app.get("/healthz")
def health():
    return {"name": settings.app_name, "env": settings.app_env, "db_configured": settings.db_configured}


# ---- 前端 SPA 托管（frontend/dist 由 Vite 构建产物）----
_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)
if os.path.isdir(os.path.join(_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")
    log.info("挂载前端静态资源：%s", _DIST)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """SPA fallback：未命中的非 API 路由一律返回 index.html。"""
    if not os.path.isdir(_DIST):
        raise HTTPException(404, "前端尚未构建")
    if full_path.startswith("api/"):
        raise HTTPException(404, "接口不存在")
    index = os.path.join(_DIST, "index.html")
    if not os.path.isfile(index):
        raise HTTPException(404, "前端尚未构建")
    return FileResponse(index)
