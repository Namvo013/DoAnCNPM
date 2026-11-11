from datetime import datetime, timezone
from typing import Any, Literal

from bson import ObjectId
from fastapi import HTTPException, status

VisitEventType = Literal["visitor_connect", "poi_enter", "poi_leave"]


class VisitService:
    async def record_connection(self, database: Any, visitor_id: str, language: str) -> ObjectId:
        result = await database.visits.insert_one(
            {
                "visitor_id": visitor_id,
                "event_type": "visitor_connect",
                "poi_id": None,
                "language": language,
                "created_at": datetime.now(timezone.utc),
            }
        )
        return result.inserted_id

    async def update_connection_location(
        self,
        database: Any,
        connection_id: ObjectId,
        latitude: float,
        longitude: float,
    ) -> None:
        await database.visits.update_one(
            {"_id": connection_id, "event_type": "visitor_connect"},
            {"$set": {"latitude": latitude, "longitude": longitude}},
        )

    async def validate_active_poi(self, database: Any, poi_id: str) -> ObjectId:
        if not ObjectId.is_valid(poi_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        object_id = ObjectId(poi_id)
        poi = await database.pois.find_one({"_id": object_id, "is_active": True})
        if poi is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active POI not found")
        return object_id

    async def record_poi_event(
        self,
        database: Any,
        visitor_id: str,
        event_type: VisitEventType,
        poi_id: ObjectId,
        language: str,
        latitude: float | None,
        longitude: float | None,
    ) -> None:
        await database.visits.insert_one(
            {
                "visitor_id": visitor_id,
                "event_type": event_type,
                "poi_id": poi_id,
                "language": language,
                "latitude": latitude,
                "longitude": longitude,
                "created_at": datetime.now(timezone.utc),
            }
        )
