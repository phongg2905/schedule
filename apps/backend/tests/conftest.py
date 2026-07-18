from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_test_database() -> None:
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret")
    os.environ.setdefault("OPENAI_API_KEY", "")
    os.environ.setdefault("ENVIRONMENT", "test")

    from src.core.config import get_settings
    from src.db import session as db_session

    get_settings.cache_clear()
    db_session._engine = None
    db_session._session_factory = None
    yield
