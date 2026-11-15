from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Admin, admin_document, parse_id
from app.schemas.auth import AdminCreate, AdminRole, AdminUpdate
from app.services.auth import admin_response, hash_password


class AdminAccountService:
    async def list(self, database: AsyncSession, limit: int) -> list[dict[str, Any]]:
        result = await database.scalars(select(Admin).order_by(Admin.email).limit(limit))
        return [admin_response(admin_document(admin)) for admin in result]

    async def create(self, database: AsyncSession, payload: AdminCreate) -> dict[str, Any]:
        admin = Admin(
            email=payload.email.strip().lower(),
            display_name=payload.display_name.strip(),
            role=payload.role.value,
            is_active=True,
            password_hash=hash_password(payload.password),
            created_at=datetime.now(timezone.utc),
        )
        database.add(admin)
        try:
            await database.commit()
        except IntegrityError as error:
            await database.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from error
        await database.refresh(admin)
        return admin_response(admin_document(admin))

    async def update(
        self,
        database: AsyncSession,
        admin_id: str,
        payload: AdminUpdate,
        current_admin: dict[str, Any],
    ) -> dict[str, Any]:
        target_id = parse_id(admin_id)
        target = await database.get(Admin, target_id) if target_id else None
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found")

        update = payload.model_dump(exclude_unset=True)
        if not update:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
        if any(value is None for value in update.values()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fields cannot be null")

        is_self = target_id == current_admin["_id"]
        requested_role = update.get("role")
        if is_self and requested_role is not None and requested_role.value != target.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot demote your own account")
        if is_self and update.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot lock your own account")

        demotes_active_super_admin = (
            target.role == AdminRole.SUPER_ADMIN.value
            and target.is_active
            and (
                (requested_role is not None and requested_role.value != AdminRole.SUPER_ADMIN.value)
                or update.get("is_active") is False
            )
        )
        if demotes_active_super_admin:
            await self._ensure_another_active_super_admin(database, target_id)

        password = update.pop("password", None)
        if requested_role is not None:
            update["role"] = requested_role.value
        if password is not None:
            update["password_hash"] = hash_password(password)
        if "display_name" in update:
            update["display_name"] = update["display_name"].strip()
        if "email" in update:
            update["email"] = update["email"].strip().lower()
        for field, value in update.items():
            setattr(target, field, value)
        target.updated_at = datetime.now(timezone.utc)
        try:
            await database.commit()
        except IntegrityError as error:
            await database.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from error
        await database.refresh(target)
        return admin_response(admin_document(target))

    async def delete(self, database: AsyncSession, admin_id: str, current_admin: dict[str, Any]) -> None:
        target_id = parse_id(admin_id)
        target = await database.get(Admin, target_id) if target_id else None
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found")
        if target_id == current_admin["_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete your own account")
        if target.role == AdminRole.SUPER_ADMIN.value and target.is_active:
            await self._ensure_another_active_super_admin(database, target_id)
        await database.delete(target)
        await database.commit()

    async def _ensure_another_active_super_admin(self, database: AsyncSession, excluded_id: str) -> None:
        count = await database.scalar(
            select(func.count())
            .select_from(Admin)
            .where(
                Admin.id != excluded_id,
                Admin.role == AdminRole.SUPER_ADMIN.value,
                Admin.is_active == true(),
            )
        )
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last active super admin",
            )
