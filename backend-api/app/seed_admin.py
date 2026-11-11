import asyncio
from datetime import datetime, timezone

from pymongo import AsyncMongoClient

from app.config import get_settings
from app.services.auth import hash_password


async def seed_super_admin() -> None:
    settings = get_settings()
    if len(settings.admin_seed_password) < 12:
        raise RuntimeError("Set ADMIN_SEED_PASSWORD to a strong password of at least 12 characters")

    client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=3000)
    try:
        database = client[settings.mongodb_database]
        if await database.admins.count_documents({}):
            raise RuntimeError("Admin accounts already exist; refusing to seed another super admin")
        await database.admins.create_index("email", unique=True)
        await database.admins.insert_one(
            {
                "email": settings.admin_seed_email.strip().lower(),
                "display_name": "Admin nhóm 2",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password(settings.admin_seed_password),
                "created_at": datetime.now(timezone.utc),
            }
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(seed_super_admin())
