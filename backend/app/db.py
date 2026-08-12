"""SQLAlchemy 引擎与会话。SQLite(开发) / PostgreSQL(生产) 自动切换。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
if _is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Postgres（Neon）：TCP keepalive + 连接超时，网络抖动时不至于被掐断长写入
    connect_args = {
        "connect_timeout": 30,
        "keepalives": 1,
        "keepalives_idle": 5,
        "keepalives_interval": 2,
        "keepalives_count": 5,
    }

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：请求级 session。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
