from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import POI, Visit, parse_id
VisitEventType = Literal["visitor_connect", "poi_enter", "poi_leave"]


class VisitService:
    async def record_connection(
        self,
        database: AsyncSession,
        visitor_id: str,
        language: str,
    ) -> str:
        event = Visit(
            visitor_id=visitor_id,
            event_type="visitor_connect",
            poi_id=None,
            language=language,
            created_at=datetime.now(timezone.utc),
        )
        database.add(event)
        await database.commit()
        await database.refresh(event)
        return event.id

    async def update_connection_location(
        self,
        database: AsyncSession,
        connection_id: str,
        latitude: float,
        longitude: float,
    ) -> None:
        event = await database.get(Visit, connection_id)
        if event is not None and event.event_type == "visitor_connect":
            event.latitude = latitude
            event.longitude = longitude
            await database.commit()

    async def validate_active_poi(self, database: AsyncSession, poi_id: str) -> str:
        valid_id = parse_id(poi_id)
        poi = await database.scalar(
            select(POI).where(POI.id == valid_id, POI.is_active == true())
        ) if valid_id else None
        if poi is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active POI not found")
        return poi.id

    async def record_poi_event(
        self,
        database: AsyncSession,
        visitor_id: str,
        event_type: VisitEventType,
        poi_id: str,
        language: str,
        latitude: float | None,
        longitude: float | None,
    ) -> None:
        event = Visit(
            visitor_id=visitor_id,
            event_type=event_type,
            poi_id=poi_id,
            language=language,
            latitude=latitude,
            longitude=longitude,
            created_at=datetime.now(timezone.utc),
        )
        database.add(event)
        await database.commit()
