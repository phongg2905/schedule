from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
from src.db.base import Base

_engine = None
_session_factory = None


def _create_engine(database_url: str):
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if "pgbouncer" in url.query:
        url = url.set(query={key: value for key, value in url.query.items() if key != "pgbouncer"})
    if url.drivername.startswith("postgresql"):
        return create_engine(url.render_as_string(hide_password=False), future=True, pool_pre_ping=True)
    if url.drivername.startswith("sqlite"):
        return create_engine(
            url.render_as_string(hide_password=False),
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    raise RuntimeError("Unsupported database driver. Configure PostgreSQL or SQLite via DATABASE_URL.")


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured.")
        _engine = _create_engine(settings.database_url)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, future=True)
    return _session_factory


def get_db() -> Session:
    return get_session_factory()()


def init_db() -> None:
    from src.db import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
