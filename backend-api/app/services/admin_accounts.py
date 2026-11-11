from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.schemas.auth import AdminCreate, AdminRole, AdminUpdate
from app.services.auth import admin_response, hash_password


class AdminAccountService:
    async def list(self, database: Any, limit: int) -> list[dict[str, Any]]:
        cursor = database.admins.find().sort("email", 1).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [admin_response(document) for document in documents]

    async def create(self, database: Any, payload: AdminCreate) -> dict[str, Any]:
        await database.admins.create_index("email", unique=True)
        now = datetime.now(timezone.utc)
        document = {
            "email": payload.email.strip().lower(),
            "display_name": payload.display_name.strip(),
            "role": payload.role.value,
            "is_active": True,
            "password_hash": hash_password(payload.password),
            "created_at": now,
        }
        try:
            result = await database.admins.insert_one(document)
        except DuplicateKeyError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from error
        document["_id"] = result.inserted_id
        return admin_response(document)

    async def update(
        self,
        database: Any,
        admin_id: str,
        payload: AdminUpdate,
        current_admin: dict[str, Any],
    ) -> dict[str, Any]:
        target_id = self._object_id(admin_id)
        target = await database.admins.find_one({"_id": target_id})
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found")

        update = payload.model_dump(exclude_unset=True)
        if not update:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
        if any(value is None for value in update.values()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fields cannot be null")

        is_self = target_id == current_admin["_id"]
        requested_role = update.get("role")
        if is_self and requested_role is not None and requested_role.value != target["role"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot demote your own account")
        if is_self and update.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot lock your own account")

        demotes_active_super_admin = (
            target.get("role") == AdminRole.SUPER_ADMIN.value
            and target.get("is_active", True)
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
            await database.admins.create_index("email", unique=True)
            update["email"] = update["email"].strip().lower()
        update["updated_at"] = datetime.now(timezone.utc)
        try:
            await database.admins.update_one({"_id": target_id}, {"$set": update})
        except DuplicateKeyError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from error
        updated = await database.admins.find_one({"_id": target_id})
        return admin_response(updated)

    async def delete(self, database: Any, admin_id: str, current_admin: dict[str, Any]) -> None:
        target_id = self._object_id(admin_id)
        target = await database.admins.find_one({"_id": target_id})
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found")
        if target_id == current_admin["_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete your own account")
        if target.get("role") == AdminRole.SUPER_ADMIN.value and target.get("is_active", True):
            await self._ensure_another_active_super_admin(database, target_id)
        await database.admins.delete_one({"_id": target_id})

    async def _ensure_another_active_super_admin(self, database: Any, excluded_id: ObjectId) -> None:
        count = await database.admins.count_documents(
            {
                "_id": {"$ne": excluded_id},
                "role": AdminRole.SUPER_ADMIN.value,
                "is_active": True,
            }
        )
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last active super admin",
            )

    @staticmethod
    def _object_id(admin_id: str) -> ObjectId:
        if not ObjectId.is_valid(admin_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin account not found")
        return ObjectId(admin_id)
