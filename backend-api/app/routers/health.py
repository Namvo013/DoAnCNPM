from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_database, get_redis
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(
    database: Any = Depends(get_database),
    redis: Any = Depends(get_redis),
) -> HealthResponse:
    result = await HealthService.check(database, redis)
    if result["status"] != "ok":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result)
    return HealthResponse(**result)
