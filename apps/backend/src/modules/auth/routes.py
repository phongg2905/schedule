from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_refresh_token_cookie, get_user_from_access_token
from src.modules.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from src.modules.auth.service import AuthService

router = APIRouter()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    from src.core.config import get_settings

    settings = get_settings()
    response.set_cookie("access_token", access_token, httponly=True, samesite="lax", secure=False, max_age=settings.access_token_minutes * 60)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="lax", secure=False, max_age=settings.refresh_token_days * 24 * 60 * 60)


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(db_session)) -> AuthResponse:
    service = AuthService(db)
    user = service.register(payload.email, payload.password, payload.name, payload.timezone)
    # Registration returns the user but does not auto-login to keep the slice explicit.
    response_model = AuthResponse(user=UserResponse(id=user.id, email=user.email, name=user.name, timezone=user.timezone, role=user.role))
    response.headers["X-Auth-Registered"] = "true"
    return response_model


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(db_session)) -> AuthResponse:
    service = AuthService(db)
    user, access_token, refresh_token = service.login(payload.email, payload.password)
    _set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(user=UserResponse(id=user.id, email=user.email, name=user.name, timezone=user.timezone, role=user.role))


@router.post("/refresh")
def refresh(response: Response, refresh_token: str = Depends(get_refresh_token_cookie), db: Session = Depends(db_session)) -> dict[str, str]:
    service = AuthService(db)
    from src.core.config import get_settings

    settings = get_settings()
    new_access_token, new_refresh_token = service.refresh(refresh_token)
    response.set_cookie("access_token", new_access_token, httponly=True, samesite="lax", secure=False, max_age=settings.access_token_minutes * 60)
    response.set_cookie("refresh_token", new_refresh_token, httponly=True, samesite="lax", secure=False, max_age=settings.refresh_token_days * 24 * 60 * 60)
    return {"status": "ok"}


@router.post("/logout")
def logout(response: Response, refresh_token: str = Depends(get_refresh_token_cookie), db: Session = Depends(db_session)) -> dict[str, str]:
    service = AuthService(db)
    service.logout(refresh_token)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_user_from_access_token)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name, timezone=user.timezone, role=user.role)
