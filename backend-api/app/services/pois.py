import math
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import POI, Translation, Visit, poi_document, parse_id
from app.schemas.poi import PoiCreate, PoiUpdate, SupportedLanguage

EARTH_RADIUS_METERS = 6_371_008.8


def to_response(document: dict[str, Any]) -> dict[str, Any]:
    longitude, latitude = document["location"]["coordinates"]
    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "geofence_radius_m": document["geofence_radius_m"],
        "image_url": document.get("image_url"),
        "category": document["category"],
        "content": document["content"],
        "name_translations": document.get("name_translations") or {},
        "category_translations": document.get("category_translations") or {},
        "audio": document.get("audio", {}),
        "is_active": document.get("is_active", True),
    }


def to_public_response(document: dict[str, Any], requested_language: SupportedLanguage) -> dict[str, Any]:
    published = document.get("published_content", document["content"])
    language = next(
        (candidate for candidate in (requested_language.value, "en", "vi") if published.get(candidate)),
        None,
    )
    if language is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI has no published content")
    response = to_response(document)
    name_translations = document.get("name_translations") or {}
    category_translations = document.get("category_translations") or {}
    response["name"] = name_translations.get(requested_language.value, document["name"])
    response["category"] = category_translations.get(requested_language.value, document["category"])
    response["content"] = {language: published[language]}
    response["content_language"] = language
    response["audio"] = {
        code: url for code, url in response["audio"].items() if code in published
    }
    return response


def _distance_meters(latitude: float, longitude: float, other_latitude: float, other_longitude: float) -> float:
    latitude_radians = math.radians(latitude)
    other_latitude_radians = math.radians(other_latitude)
    delta_latitude = other_latitude_radians - latitude_radians
    delta_longitude = math.radians(other_longitude - longitude)
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_radians)
        * math.cos(other_latitude_radians)
        * math.sin(delta_longitude / 2) ** 2
    )
    return EARTH_RADIUS_METERS * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


class PoiService:
    async def list_admin(
        self,
        database: AsyncSession,
        limit: int,
        skip: int,
    ) -> tuple[list[dict[str, Any]], int]:
        condition = POI.parent_poi_id.is_(None)
        result = await database.scalars(
            select(POI).where(condition).order_by(POI.name).offset(skip).limit(limit)
        )
        total = await database.scalar(select(func.count()).select_from(POI).where(condition))
        return [to_response(poi_document(poi)) for poi in result], int(total or 0)

    async def create(self, database: AsyncSession, payload: PoiCreate) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        data = payload.model_dump()
        coordinates = data.pop("coordinates")
        poi = POI(
            **data,
            latitude=coordinates["latitude"],
            longitude=coordinates["longitude"],
            published_content=dict(data["content"]),
            audio={},
            created_at=now,
            updated_at=now,
        )
        database.add(poi)
        await database.commit()
        await database.refresh(poi)
        return to_response(poi_document(poi))

    async def get_public(
        self,
        database: AsyncSession,
        poi_id: str,
        language: SupportedLanguage = SupportedLanguage.VI,
    ) -> dict[str, Any]:
        poi = await self._find(database, poi_id)
        if not poi.is_active or poi.parent_poi_id is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        return to_public_response(poi_document(poi), language)

    async def list_public(
        self,
        database: AsyncSession,
        limit: int,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_m: int | None = None,
        language: SupportedLanguage = SupportedLanguage.VI,
    ) -> list[dict[str, Any]]:
        conditions = [POI.is_active == true(), POI.parent_poi_id.is_(None)]
        if latitude is not None and longitude is not None and radius_m is not None:
            latitude_delta = radius_m / 111_320
            longitude_delta = min(
                180,
                radius_m / max(111_320 * abs(math.cos(math.radians(latitude))), 1),
            )
            conditions.extend(
                (
                    POI.latitude >= latitude - latitude_delta,
                    POI.latitude <= latitude + latitude_delta,
                )
            )
            min_longitude = longitude - longitude_delta
            max_longitude = longitude + longitude_delta
            if min_longitude < -180:
                conditions.append(or_(POI.longitude >= min_longitude + 360, POI.longitude <= max_longitude))
            elif max_longitude > 180:
                conditions.append(or_(POI.longitude >= min_longitude, POI.longitude <= max_longitude - 360))
            else:
                conditions.extend((POI.longitude >= min_longitude, POI.longitude <= max_longitude))

        pois = list(await database.scalars(select(POI).where(*conditions)))
        documents = [poi_document(poi) for poi in pois]
        if latitude is not None and longitude is not None and radius_m is not None:
            documents = [
                document
                for document in documents
                if _distance_meters(
                    latitude,
                    longitude,
                    document["location"]["coordinates"][1],
                    document["location"]["coordinates"][0],
                )
                <= radius_m
            ]
            documents.sort(
                key=lambda document: _distance_meters(
                    latitude,
                    longitude,
                    document["location"]["coordinates"][1],
                    document["location"]["coordinates"][0],
                )
            )
        return [to_public_response(document, language) for document in documents[:limit]]

    async def update(self, database: AsyncSession, poi_id: str, payload: PoiUpdate) -> dict[str, Any]:
        poi = await self._find(database, poi_id)
        update = payload.model_dump(exclude_unset=True)
        if not update:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
        if any(value is None for key, value in update.items() if key != "image_url"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fields cannot be null")
        coordinates = update.pop("coordinates", None)
        if "content" in update:
            update["published_content"] = dict(update["content"])
        if coordinates is not None:
            update["latitude"] = coordinates["latitude"]
            update["longitude"] = coordinates["longitude"]
        for field, value in update.items():
            setattr(poi, field, value)
        poi.updated_at = datetime.now(timezone.utc)
        await database.commit()
        await database.refresh(poi)
        return to_response(poi_document(poi))

    async def delete(self, database: AsyncSession, poi_id: str) -> None:
        poi = await self._find(database, poi_id)
        children = await database.scalars(select(POI).where(POI.parent_poi_id == poi.id))
        for child in children:
            child.parent_poi_id = None
        await database.execute(delete(Translation).where(Translation.poi_id == poi.id))
        await database.execute(update(Visit).where(Visit.poi_id == poi.id).values(poi_id=None))
        await database.delete(poi)
        await database.commit()

    async def _find(self, database: AsyncSession, poi_id: str) -> POI:
        valid_id = parse_id(poi_id)
        poi = await database.get(POI, valid_id) if valid_id else None
        if poi is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        return poi
