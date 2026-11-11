from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.schemas.poi import PoiCreate, PoiUpdate, SupportedLanguage


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


class PoiService:
    async def list_admin(
        self,
        database: Any,
        limit: int,
        skip: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"parent_poi_id": None}
        cursor = database.pois.find(query).sort("name", 1).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        total = await database.pois.count_documents(query)
        return [to_response(document) for document in documents], total

    async def create(self, database: Any, payload: PoiCreate) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        data = payload.model_dump()
        coordinates = data.pop("coordinates")
        document = {
            **data,
            "location": {
                "type": "Point",
                "coordinates": [coordinates["longitude"], coordinates["latitude"]],
            },
            "published_content": dict(data["content"]),
            "is_active": data["is_active"],
            "created_at": now,
            "updated_at": now,
        }
        result = await database.pois.insert_one(document)
        document["_id"] = result.inserted_id
        return to_response(document)

    async def get_public(
        self,
        database: Any,
        poi_id: str,
        language: SupportedLanguage = SupportedLanguage.VI,
    ) -> dict[str, Any]:
        document = await self._find(
            database,
            poi_id,
            {"is_active": True, "parent_poi_id": None},
        )
        return to_public_response(document, language)

    async def list_public(
        self,
        database: Any,
        limit: int,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_m: int | None = None,
        language: SupportedLanguage = SupportedLanguage.VI,
    ) -> list[dict[str, Any]]:
        if latitude is not None and longitude is not None and radius_m is not None:
            await database.pois.create_index([("location", "2dsphere")])
            query = {
                "is_active": True,
                "parent_poi_id": None,
                "location": {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [longitude, latitude],
                        },
                        "$maxDistance": radius_m,
                    }
                },
            }
        else:
            query = {"is_active": True, "parent_poi_id": None}
        cursor = database.pois.find(query).limit(limit)
        documents = await cursor.to_list(length=limit)
        return [to_public_response(document, language) for document in documents]

    async def update(self, database: Any, poi_id: str, payload: PoiUpdate) -> dict[str, Any]:
        update = payload.model_dump(exclude_unset=True)
        if not update:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
        if any(value is None for key, value in update.items() if key != "image_url"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Fields cannot be null")
        coordinates = update.pop("coordinates", None)
        if "content" in update:
            update["published_content"] = dict(update["content"])
        if coordinates is not None:
            update["location"] = {
                "type": "Point",
                "coordinates": [coordinates["longitude"], coordinates["latitude"]],
            }
        update["updated_at"] = datetime.now(timezone.utc)
        result = await database.pois.update_one({"_id": self._object_id(poi_id)}, {"$set": update})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        document = await database.pois.find_one({"_id": self._object_id(poi_id)})
        return to_response(document)

    async def delete(self, database: Any, poi_id: str) -> None:
        object_id = self._object_id(poi_id)
        result = await database.pois.delete_one({"_id": object_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")

    async def _find(
        self,
        database: Any,
        poi_id: str,
        extra_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {"_id": self._object_id(poi_id)}
        if extra_filter:
            query.update(extra_filter)
        document = await database.pois.find_one(query)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        return document

    @staticmethod
    def _object_id(poi_id: str) -> ObjectId:
        if not ObjectId.is_valid(poi_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        return ObjectId(poi_id)
