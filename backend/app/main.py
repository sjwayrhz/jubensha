import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@app.get("/")
def health():
    return {"name": settings.app_name, "env": settings.app_env, "db_configured": settings.db_configured}
