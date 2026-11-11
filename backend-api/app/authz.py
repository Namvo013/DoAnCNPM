from collections.abc import Callable
from typing import Any

from fastapi import Cookie, Depends, HTTPException, status

from app.database import get_database, get_redis
from app.schemas.auth import AdminRole
from app.services.auth import COOKIE_NAME, AuthService

auth_service = AuthService()

ROLE_PERMISSIONS: dict[AdminRole, frozenset[str]] = {
    AdminRole.SUPER_ADMIN: frozenset({"*"}),
    AdminRole.AREA_OPERATOR: frozenset(
        {"poi:read", "poi:write", "visitor:read", "heatmap:read"}
    ),
    AdminRole.CONTENT_EDITOR: frozenset({"poi:read", "content:write"}),
    AdminRole.ANALYTICS_VIEWER: frozenset({"analytics:read", "visitor:read", "heatmap:read"}),
}


def has_permission(role: str, permission: str) -> bool:
    try:
        admin_role = AdminRole(role)
    except ValueError:
        return False
    permissions = ROLE_PERMISSIONS.get(admin_role, frozenset())
    return "*" in permissions or permission in permissions


async def get_current_admin(
    database: Any = Depends(get_database),
    redis: Any = Depends(get_redis),
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> dict[str, Any]:
    return await auth_service.get_current_admin(database, redis, token)


def require_roles(*roles: AdminRole) -> Callable[..., Any]:
    allowed_roles = frozenset(role.value for role in roles)

    async def guard(admin: dict[str, Any] = Depends(get_current_admin)) -> dict[str, Any]:
        if admin.get("role") not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return admin

    return guard


def require_permission(permission: str) -> Callable[..., Any]:
    async def guard(admin: dict[str, Any] = Depends(get_current_admin)) -> dict[str, Any]:
        if not has_permission(admin.get("role", ""), permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return admin

    return guard
