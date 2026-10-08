"""SQLAlchemy engine（PyMySQL 连 TiDB）。连接失败时启动不崩，由 main.py 降级处理。"""
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..core.config import settings

log = logging.getLogger("jubensha.db")


class Base(DeclarativeBase):
    pass


def _make_engine():
    connect_args: dict = {}
    if settings.tidb_ssl_ca:
        connect_args["ssl"] = {"ca": settings.tidb_ssl_ca}
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> None:
    """启动时探测数据库；失败抛异常，main.py 捕获后降级为警告（应用不崩）。"""
    if not settings.db_configured:
        raise RuntimeError(
            "数据库未配置：请设置环境变量 TIDB_HOST / TIDB_USER / TIDB_PASSWORD（详见 README）"
        )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        raise RuntimeError(f"无法连接 TiDB {settings.tidb_host}:{settings.tidb_port}/{settings.tidb_db}：{e}")
