from collections.abc import Generator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.security import decode_token
from src.db.models import User
from src.db.session import get_db


def db_session() -> Generator[Session, None, None]:
    db = get_db()
    try:
        yield db
    finally:
        db.close()


def get_user_from_access_token(access_token: str | None = Cookie(default=None), db: Session = Depends(db_session)) -> User:
    settings = get_settings()
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_UNAUTHORIZED")

    try:
        payload = decode_token(access_token, settings.jwt_secret)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_UNAUTHORIZED") from exc

    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_UNAUTHORIZED")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_UNAUTHORIZED")
    return user


def get_refresh_token_cookie(refresh_token: str | None = Cookie(default=None)) -> str:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_UNAUTHORIZED")
    return refresh_token
