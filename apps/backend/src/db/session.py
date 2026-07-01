from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings
from src.db.base import Base

_engine = None
_session_factory = None


def _create_engine():
    settings = get_settings()
    return create_engine(settings.database_url, future=True, pool_pre_ping=True)


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
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

    settings = get_settings()
    engine = get_engine()
    if settings.database_url.startswith("sqlite"):
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
