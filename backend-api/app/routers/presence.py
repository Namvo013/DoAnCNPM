import asyncio
import json
import secrets
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, WebSocket, WebSocketDisconnect
from bson import ObjectId
from pydantic import ValidationError

from app.authz import auth_service, has_permission
from app.database import get_websocket_database, get_websocket_redis
from app.schemas.poi import SupportedLanguage
from app.schemas.presence import VisitorHeartbeat
from app.services.auth import COOKIE_NAME
from app.services.presence import PRESENCE_CHANNEL, PresenceService
from app.services.visits import VisitService

router = APIRouter(tags=["realtime presence"])
root_websocket_router = APIRouter(tags=["realtime presence"])
presence_service = PresenceService()
visit_service = VisitService()


@router.websocket("/ws/tourist")
@router.websocket("/ws/visitors")
async def visitor_presence(
    websocket: WebSocket,
    database: Any = Depends(get_websocket_database),
    redis: Any = Depends(get_websocket_redis),
    language: SupportedLanguage = SupportedLanguage.VI,
) -> None:
    selected_language = language
    await websocket.accept()
    visitor_id = secrets.token_urlsafe(18)
    current_poi_id: str | None = None
    current_poi_object_id: ObjectId | None = None
    current_language = selected_language.value
    tasks: set[asyncio.Task[None]] = set()
    registered = False
    connection_event_id: ObjectId | None = None

    async def receive_heartbeats() -> None:
        nonlocal current_poi_id, current_poi_object_id, current_language
        while True:
            try:
                message = VisitorHeartbeat.model_validate(await websocket.receive_json())
            except ValidationError:
                await websocket.send_json({"type": "error", "detail": "Expected a heartbeat message"})
                continue
            if message.language is not None:
                current_language = message.language.value
            if (
                connection_event_id is not None
                and message.latitude is not None
                and message.longitude is not None
            ):
                await visit_service.update_connection_location(
                    database,
                    connection_event_id,
                    message.latitude,
                    message.longitude,
                )
            if "poi_id" in message.model_fields_set and message.poi_id != current_poi_id:
                poi_object_id = None
                if message.poi_id is not None:
                    try:
                        poi_object_id = await visit_service.validate_active_poi(database, message.poi_id)
                    except HTTPException as error:
                        await websocket.send_json({"type": "error", "detail": error.detail})
                        continue
                if current_poi_id is not None and current_poi_object_id is not None:
                    await visit_service.record_poi_event(
                        database,
                        visitor_id,
                        "poi_leave",
                        current_poi_object_id,
                        current_language,
                        message.latitude,
                        message.longitude,
                    )
                current_poi_id = None
                current_poi_object_id = None
                if message.poi_id is not None and poi_object_id is not None:
                    await visit_service.record_poi_event(
                        database,
                        visitor_id,
                        "poi_enter",
                        poi_object_id,
                        current_language,
                        message.latitude,
                        message.longitude,
                    )
                    current_poi_id = str(poi_object_id)
                    current_poi_object_id = poi_object_id
            count = await presence_service.heartbeat(
                redis,
                visitor_id,
                database,
                message.latitude,
                message.longitude,
                current_poi_id,
            )
            await websocket.send_json({"type": "heartbeat_ack", "online": count})

    try:
        connection_event_id = await visit_service.record_connection(database, visitor_id, current_language)
        count = await presence_service.connect(redis, visitor_id)
        registered = True
        await websocket.send_json(
            {
                "type": "connected",
                "visitor_id": visitor_id,
                "online": count,
                "language": current_language,
                "heartbeat_interval_seconds": 15,
                "stale_after_seconds": 45,
            }
        )
        tasks = {
            asyncio.create_task(receive_heartbeats()),
        }
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.exception() is not None:
                raise task.exception()
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        try:
            if current_poi_object_id is not None:
                await visit_service.record_poi_event(
                    database,
                    visitor_id,
                    "poi_leave",
                    current_poi_object_id,
                    current_language,
                    None,
                    None,
                )
        finally:
            if registered:
                await presence_service.disconnect(redis, visitor_id, database)


@router.websocket("/ws/admin")
@router.websocket("/ws/admin/presence")
async def admin_presence(
    websocket: WebSocket,
    database: Any = Depends(get_websocket_database),
    redis: Any = Depends(get_websocket_redis),
    token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> None:
    try:
        admin = await auth_service.get_current_admin(database, redis, token)
    except HTTPException:
        await websocket.close(code=4401, reason="Authentication required")
        return
    if not has_permission(admin.get("role", ""), "visitor:read"):
        await websocket.close(code=4403, reason="Insufficient permission")
        return

    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe(PRESENCE_CHANNEL)
    current_snapshot = await presence_service.snapshot(redis)
    current_count = current_snapshot["online"]
    await websocket.send_json({"type": "presence", **current_snapshot})

    async def stream_updates() -> None:
        nonlocal current_count
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and message.get("data"):
                event = json.loads(message["data"])
                current_count = event["online"]
                await websocket.send_json(event)
            count = await presence_service.online_count(redis)
            if count != current_count:
                snapshot = await presence_service.snapshot(redis)
                current_count = snapshot["online"]
                await websocket.send_json({"type": "presence", **snapshot})

    async def watch_disconnect() -> None:
        while True:
            await websocket.receive_text()

    tasks: set[asyncio.Task[None]] = {
        asyncio.create_task(stream_updates()),
        asyncio.create_task(watch_disconnect()),
    }
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.exception() is not None:
                raise task.exception()
    except WebSocketDisconnect:
        pass
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await pubsub.unsubscribe(PRESENCE_CHANNEL)
        await pubsub.aclose()


root_websocket_router.add_api_websocket_route("/ws/tourist", visitor_presence)
root_websocket_router.add_api_websocket_route("/ws/admin", admin_presence)
