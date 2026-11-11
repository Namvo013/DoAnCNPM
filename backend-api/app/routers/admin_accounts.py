from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.authz import require_roles
from app.database import get_database
from app.schemas.auth import AdminCreate, AdminListResponse, AdminResponse, AdminRole, AdminUpdate
from app.services.admin_accounts import AdminAccountService

router = APIRouter(prefix="/admin/admins", tags=["admin account management"])
admin_account_service = AdminAccountService()
super_admin = require_roles(AdminRole.SUPER_ADMIN)


@router.get("", response_model=AdminListResponse)
async def list_admins(
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(super_admin),
    limit: int = Query(default=100, ge=1, le=500),
) -> AdminListResponse:
    items = await admin_account_service.list(database, limit)
    return AdminListResponse(items=items, total=len(items))


@router.post("", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    payload: AdminCreate,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(super_admin),
) -> AdminResponse:
    return AdminResponse(**await admin_account_service.create(database, payload))


@router.patch("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: str,
    payload: AdminUpdate,
    database: Any = Depends(get_database),
    current_admin: dict[str, Any] = Depends(super_admin),
) -> AdminResponse:
    return AdminResponse(
        **await admin_account_service.update(database, admin_id, payload, current_admin)
    )


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: str,
    database: Any = Depends(get_database),
    current_admin: dict[str, Any] = Depends(super_admin),
) -> Response:
    await admin_account_service.delete(database, admin_id, current_admin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
