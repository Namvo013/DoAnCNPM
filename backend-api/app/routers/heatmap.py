from typing import Any

from fastapi import APIRouter, Depends

from app.authz import require_permission
from app.database import get_database
from app.schemas.heatmap import HeatmapResponse
from app.services.presence import PresenceService

router = APIRouter(prefix="/admin/heatmap", tags=["visitor heatmap"])
presence_service = PresenceService()


@router.get("", response_model=HeatmapResponse)
async def get_heatmap(
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("heatmap:read")),
) -> HeatmapResponse:
    return HeatmapResponse(**await presence_service.heatmap(database))
