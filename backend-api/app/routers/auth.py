from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.config import get_settings
from app.database import get_database, get_redis
from app.schemas.auth import AdminResponse, AuthMessage, LoginRequest
from app.services.auth import COOKIE_NAME, AuthService, admin_response

router = APIRouter(prefix="/auth", tags=["admin authentication"])
auth_service = AuthService()


@router.post("/login", response_model=AdminResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    database: Any = Depends(get_database),
) -> AdminResponse:
    admin, token, expires_at = await auth_service.login(database, payload.email, payload.password)
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        expires=expires_at,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return AdminResponse(**admin)


@router.post("/logout", response_model=AuthMessage)
async def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    redis: Any = Depends(get_redis),
) -> AuthMessage:
    await auth_service.logout(redis, token)
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite=get_settings().cookie_samesite,
    )
    return AuthMessage(message="Logged out")


@router.get("/me", response_model=AdminResponse)
async def me(
    database: Any = Depends(get_database),
    redis: Any = Depends(get_redis),
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> AdminResponse:
    admin = await auth_service.get_current_admin(database, redis, token)
    return AdminResponse(**admin_response(admin))
