import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Admin, Base
from app.services.auth import hash_password


async def seed_super_admin() -> None:
    settings = get_settings()
    if len(settings.admin_seed_password) < 12:
        raise RuntimeError("Set ADMIN_SEED_PASSWORD to a strong password of at least 12 characters")

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            count = await session.scalar(select(func.count()).select_from(Admin))
            if count:
                raise RuntimeError("Admin accounts already exist; refusing to seed another super admin")
            session.add(
                Admin(
                    email=settings.admin_seed_email.strip().lower(),
                    display_name="Admin nhóm 2",
                    role="super_admin",
                    is_active=True,
                    password_hash=hash_password(settings.admin_seed_password),
                    created_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_super_admin())
