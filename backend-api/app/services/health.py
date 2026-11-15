import asyncio
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


class HealthService:
    @staticmethod
    async def check(database: Any, redis: Any) -> dict[str, str]:
        database_status, redis_status = "ok", "ok"
        try:
            await database.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError, TimeoutError, asyncio.TimeoutError):
            database_status = "unavailable"

        try:
            await redis.ping()
        except (RedisError, OSError, TimeoutError, asyncio.TimeoutError):
            redis_status = "unavailable"

        overall = "ok" if database_status == redis_status == "ok" else "unavailable"
        return {"status": overall, "sql_server": database_status, "redis": redis_status}
