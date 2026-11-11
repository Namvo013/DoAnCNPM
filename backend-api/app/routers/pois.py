from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.authz import require_permission
from app.database import get_database
from app.schemas.poi import PoiCreate, PoiListResponse, PoiResponse, PoiUpdate, SupportedLanguage
from app.services.pois import PoiService

public_router = APIRouter(prefix="/pois", tags=["POIs"])
admin_router = APIRouter(prefix="/admin/pois", tags=["admin POIs"])
poi_service = PoiService()


@public_router.get("", response_model=PoiListResponse)
async def list_pois(
    database: Any = Depends(get_database),
    limit: int = Query(default=50, ge=1, le=100),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_m: int | None = Query(default=None, gt=0, le=100_000),
    language: SupportedLanguage = Query(default=SupportedLanguage.VI),
) -> PoiListResponse:
    supplied = (latitude is not None, longitude is not None, radius_m is not None)
    if any(supplied) and not all(supplied):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="latitude, longitude and radius_m must be provided together",
        )
    items = await poi_service.list_public(database, limit, latitude, longitude, radius_m, language)
    return PoiListResponse(items=items, total=len(items))


@public_router.get("/{poi_id}", response_model=PoiResponse)
async def get_poi(
    poi_id: str,
    database: Any = Depends(get_database),
    language: SupportedLanguage = Query(default=SupportedLanguage.VI),
) -> PoiResponse:
    return PoiResponse(**await poi_service.get_public(database, poi_id, language))


@admin_router.get("", response_model=PoiListResponse)
async def list_admin_pois(
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("poi:read")),
    limit: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
) -> PoiListResponse:
    items, total = await poi_service.list_admin(database, limit, skip)
    return PoiListResponse(items=items, total=total)


@admin_router.post("", response_model=PoiResponse, status_code=status.HTTP_201_CREATED)
async def create_poi(
    payload: PoiCreate,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("poi:write")),
) -> PoiResponse:
    return PoiResponse(**await poi_service.create(database, payload))


@admin_router.put("/{poi_id}", response_model=PoiResponse)
async def update_poi(
    poi_id: str,
    payload: PoiUpdate,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("poi:write")),
) -> PoiResponse:
    return PoiResponse(**await poi_service.update(database, poi_id, payload))


@admin_router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poi(
    poi_id: str,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("poi:write")),
) -> None:
    await poi_service.delete(database, poi_id)
