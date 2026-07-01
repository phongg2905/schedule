from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.security import create_access_token, create_refresh_token, decode_token, hash_password, token_hash, verify_password
from src.db.models import RefreshToken, User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, email: str, password: str, name: str, timezone: str) -> User:
        existing = self.db.query(User).filter(User.email == email).one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        user = User(email=email, password_hash=hash_password(password), name=name, timezone=timezone)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, email: str, password: str) -> tuple[User, str, str]:
        user = self.db.query(User).filter(User.email == email).one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        token_row = RefreshToken(
            user_id=user.id,
            token_hash=token_hash(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days),
        )
        self.db.add(token_row)
        self.db.commit()
        return user, access_token, refresh_token

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        settings = get_settings()
        try:
            payload = decode_token(refresh_token, settings.jwt_refresh_secret)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
        if payload.get("typ") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user_id = payload.get("sub")
        token_row = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.token_hash == token_hash(refresh_token), RefreshToken.revoked_at.is_(None))
            .one_or_none()
        )
        if not token_row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        token_row.revoked_at = datetime.now(UTC)
        access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)
        self.db.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash(new_refresh_token),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
            )
        )
        self.db.commit()
        return access_token, new_refresh_token

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token, get_settings().jwt_refresh_secret)
        except Exception:
            return
        user_id = payload.get("sub")
        token_row = self.db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.token_hash == token_hash(refresh_token), RefreshToken.revoked_at.is_(None)).one_or_none()
        if token_row:
            token_row.revoked_at = datetime.now(UTC)
            self.db.commit()
