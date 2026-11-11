import json
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings

PRESENCE_KEY = "presence:visitors"
PRESENCE_POI_KEY = "presence:visitor-pois"
PRESENCE_CHANNEL = "presence:updates"
VISITOR_TIMEOUT_SECONDS = 45
EARTH_RADIUS_METERS = 6_371_008.8
POI_CROWD_THRESHOLD = 50


def _distance_meters(first: tuple[float, float], second: tuple[float, float]) -> float:
    first_lat, first_lon = map(math.radians, first)
    second_lat, second_lon = map(math.radians, second)
    delta_lat = second_lat - first_lat
    delta_lon = second_lon - first_lon
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(first_lat) * math.cos(second_lat) * math.sin(delta_lon / 2) ** 2
    )
    return EARTH_RADIUS_METERS * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


class PresenceService:
    async def _prune_and_count(self, redis: Any, now: float) -> int:
        await redis.zremrangebyscore(PRESENCE_KEY, "-inf", now - VISITOR_TIMEOUT_SECONDS)
        return int(await redis.zcard(PRESENCE_KEY))

    async def _broadcast(self, redis: Any, count: int) -> None:
        active_visitors = set(await redis.zrange(PRESENCE_KEY, 0, -1))
        visitor_pois = await redis.hgetall(PRESENCE_POI_KEY)
        poi_counts: dict[str, int] = {}
        for visitor_id, poi_id in visitor_pois.items():
            if visitor_id in active_visitors:
                poi_counts[poi_id] = poi_counts.get(poi_id, 0) + 1
        await redis.publish(
            PRESENCE_CHANNEL,
            json.dumps(
                {
                    "type": "presence",
                    "online": count,
                    "poi_counts": [
                        {
                            "poi_id": poi_id,
                            "visitor_count": visitor_count,
                            "warning": visitor_count > POI_CROWD_THRESHOLD,
                        }
                        for poi_id, visitor_count in poi_counts.items()
                    ],
                }
            ),
        )

    async def snapshot(self, redis: Any) -> dict[str, Any]:
        count = await self._prune_and_count(redis, time.time())
        active_visitors = set(await redis.zrange(PRESENCE_KEY, 0, -1))
        visitor_pois = await redis.hgetall(PRESENCE_POI_KEY)
        poi_counts: dict[str, int] = {}
        stale_visitors = set(visitor_pois) - active_visitors
        if stale_visitors:
            await redis.hdel(PRESENCE_POI_KEY, *stale_visitors)
        for visitor_id, poi_id in visitor_pois.items():
            if visitor_id in active_visitors:
                poi_counts[poi_id] = poi_counts.get(poi_id, 0) + 1
        return {
            "online": count,
            "poi_counts": [
                {
                    "poi_id": poi_id,
                    "visitor_count": visitor_count,
                    "warning": visitor_count > POI_CROWD_THRESHOLD,
                }
                for poi_id, visitor_count in poi_counts.items()
            ],
        }

    async def connect(self, redis: Any, visitor_id: str) -> int:
        now = time.time()
        await redis.zadd(PRESENCE_KEY, {visitor_id: now})
        await redis.expire(PRESENCE_KEY, VISITOR_TIMEOUT_SECONDS * 2)
        count = await self._prune_and_count(redis, now)
        await self._broadcast(redis, count)
        return count

    async def heartbeat(
        self,
        redis: Any,
        visitor_id: str,
        database: Any,
        latitude: float | None = None,
        longitude: float | None = None,
        poi_id: str | None = None,
    ) -> int:
        now = time.time()
        await redis.zadd(PRESENCE_KEY, {visitor_id: now})
        await redis.expire(PRESENCE_KEY, VISITOR_TIMEOUT_SECONDS * 2)
        if poi_id is None:
            await redis.hdel(PRESENCE_POI_KEY, visitor_id)
        else:
            await redis.hset(PRESENCE_POI_KEY, visitor_id, poi_id)
        if latitude is not None and longitude is not None:
            current_time = datetime.fromtimestamp(now, timezone.utc)
            await database.visitor_locations.update_one(
                {"visitor_id": visitor_id},
                {
                    "$set": {
                        "location": {
                            "type": "Point",
                            "coordinates": [longitude, latitude],
                        },
                        "latitude": latitude,
                        "longitude": longitude,
                        "last_seen": current_time,
                    },
                    "$setOnInsert": {"created_at": current_time},
                },
                upsert=True,
            )
        count = await self._prune_and_count(redis, now)
        await self._broadcast(redis, count)
        return count

    async def disconnect(self, redis: Any, visitor_id: str, database: Any | None = None) -> int:
        now = time.time()
        await redis.zrem(PRESENCE_KEY, visitor_id)
        await redis.hdel(PRESENCE_POI_KEY, visitor_id)
        if database is not None:
            await database.visitor_locations.delete_one({"visitor_id": visitor_id})
        count = await self._prune_and_count(redis, now)
        await self._broadcast(redis, count)
        return count

    async def online_count(self, redis: Any) -> int:
        return await self._prune_and_count(redis, time.time())

    async def heatmap(self, database: Any) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        await database.visitor_locations.create_index("last_seen", expireAfterSeconds=60)
        cursor = database.visitor_locations.find(
            {"last_seen": {"$gte": now - timedelta(seconds=VISITOR_TIMEOUT_SECONDS)}}
        )
        visitors = await cursor.to_list(length=10_000)
        grid_size = get_settings().heatmap_grid_size_meters
        cells: dict[tuple[int, int], dict[str, float | int]] = {}
        for visitor in visitors:
            latitude, longitude = visitor["latitude"], visitor["longitude"]
            x, y = self._project(latitude, longitude)
            cell_key = (math.floor(x / grid_size), math.floor(y / grid_size))
            cell = cells.setdefault(cell_key, {"x": 0.0, "y": 0.0, "count": 0})
            cell["x"] = cell_key[0] * grid_size + grid_size / 2
            cell["y"] = cell_key[1] * grid_size + grid_size / 2
            cell["count"] = int(cell["count"]) + 1

        response_cells = []
        for cell in cells.values():
            latitude, longitude = self._unproject(float(cell["x"]), float(cell["y"]))
            count = int(cell["count"])
            response_cells.append(
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "count": count,
                    "warning": count > POI_CROWD_THRESHOLD,
                }
            )

        poi_cursor = database.pois.find({"is_active": True})
        pois = await poi_cursor.to_list(length=10_000)
        poi_crowds = []
        for poi in pois:
            longitude, latitude = poi["location"]["coordinates"]
            count = sum(
                _distance_meters((latitude, longitude), (visitor["latitude"], visitor["longitude"]))
                <= poi["geofence_radius_m"]
                for visitor in visitors
            )
            poi_crowds.append(
                {
                    "poi_id": str(poi["_id"]),
                    "name": poi["name"],
                    "visitor_count": count,
                    "warning": count > POI_CROWD_THRESHOLD,
                }
            )
        return {
            "cells": response_cells,
            "poi_crowds": poi_crowds,
            "located_visitors": len(visitors),
            "crowd_threshold": POI_CROWD_THRESHOLD,
        }

    @staticmethod
    def _project(latitude: float, longitude: float) -> tuple[float, float]:
        earth_radius = 6_378_137
        clamped_latitude = max(min(latitude, 85.05112878), -85.05112878)
        x = earth_radius * math.radians(longitude)
        y = earth_radius * math.log(
            math.tan(math.pi / 4 + math.radians(clamped_latitude) / 2)
        )
        return x, y

    @staticmethod
    def _unproject(x: float, y: float) -> tuple[float, float]:
        earth_radius = 6_378_137
        longitude = math.degrees(x / earth_radius)
        latitude = math.degrees(2 * math.atan(math.exp(y / earth_radius)) - math.pi / 2)
        return latitude, longitude
