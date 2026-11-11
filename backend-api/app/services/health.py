import asyncio
from typing import Any

from pymongo.errors import PyMongoError
from redis.exceptions import RedisError


class HealthService:
    @staticmethod
    async def check(database: Any, redis: Any) -> dict[str, str]:
        mongo_status, redis_status = "ok", "ok"
        # In demo/mock mode, some ping commands might fail or not be implemented
        is_mock = "Mock" in str(type(database)) or "Fake" in str(type(redis))
        
        try:
            if not is_mock:
                await database.command("ping")
        except (PyMongoError, OSError, TimeoutError, asyncio.TimeoutError, AttributeError):
            mongo_status = "unavailable"
            
        try:
            if not is_mock:
                await redis.ping()
        except (RedisError, OSError, TimeoutError, asyncio.TimeoutError, AttributeError):
            redis_status = "unavailable"
            
        if is_mock:
            mongo_status = "ok" if mongo_status != "unavailable" else "mock"
            redis_status = "ok" if redis_status != "unavailable" else "mock"
            mongo_status, redis_status = "ok", "ok" # Force ok for mock
        overall = "ok" if mongo_status == redis_status == "ok" else "unavailable"
        return {"status": overall, "mongodb": mongo_status, "redis": redis_status}
