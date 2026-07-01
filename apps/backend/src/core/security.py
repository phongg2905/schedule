import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from typing import Any

import jwt
from passlib.context import CryptContext

from src.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(subject: str, secret: str, expires_delta: timedelta, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return create_token(subject, settings.jwt_secret, timedelta(minutes=settings.access_token_minutes), "access")


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return create_token(subject, settings.jwt_refresh_secret, timedelta(days=settings.refresh_token_days), "refresh")


def decode_token(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=["HS256"])


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
