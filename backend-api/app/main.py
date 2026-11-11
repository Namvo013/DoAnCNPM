import asyncio
import inspect
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import AsyncMongoClient
from redis.exceptions import RedisError
from redis.asyncio import Redis

from app.config import get_settings
from app.routers.auth import router as auth_router
from app.routers.audio import router as audio_router
from app.routers.admin_accounts import router as admin_accounts_router
from app.routers.access_qr import router as access_qr_router
from app.routers.analytics import router as analytics_router
from app.routers.health import router as health_router
from app.routers.heatmap import router as heatmap_router
from app.routers.images import router as images_router
from app.routers.pois import admin_router as admin_poi_router
from app.routers.pois import public_router as public_poi_router
from app.routers.presence import root_websocket_router, router as presence_router
from app.routers.translations import preview_router as translation_preview_router
from app.routers.translations import router as translations_router
from app.services.presence import PRESENCE_CHANNEL, PresenceService
from app.services.auth import hash_password

logger = logging.getLogger(__name__)


async def cleanup_stale_visitors(redis: Redis) -> None:
    presence_service = PresenceService()
    while True:
        await asyncio.sleep(5)
        try:
            snapshot = await presence_service.snapshot(redis)
            await redis.publish(
                PRESENCE_CHANNEL,
                json.dumps({"type": "presence", **snapshot}),
            )
        except (RedisError, OSError, TimeoutError):
            logger.exception("Unable to clean stale visitor presence entries")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.demo_mode:
        if settings.environment.lower() != "development":
            raise RuntimeError("DEMO_MODE is only available when ENVIRONMENT=development")
        from fakeredis.aioredis import FakeRedis
        from mongomock_motor import AsyncMongoMockClient

        mongo_client = AsyncMongoMockClient()
        redis_client = FakeRedis(decode_responses=True)
        logger.warning("DEMO_MODE enabled: using in-memory MongoDB and Redis substitutes")
    else:
        mongo_client = AsyncMongoClient(settings.mongodb_url, serverSelectionTimeoutMS=3000)
        redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            protocol=2,
        )
    app.state.mongo_client = mongo_client
    app.state.database = mongo_client[settings.mongodb_database]
    app.state.redis = redis_client
    if settings.demo_mode:
        await app.state.database.admins.create_index("email", unique=True)
        await app.state.database.admins.insert_one(
            {
                "email": settings.admin_seed_email.strip().lower(),
                "display_name": "Admin nhóm 2",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password(settings.admin_seed_password),
                "created_at": datetime.now(timezone.utc),
            }
        )
    cleanup_task = None
    if not getattr(app.state, "disable_background_tasks", False):
        cleanup_task = asyncio.create_task(cleanup_stale_visitors(redis_client))
    try:
        yield
    finally:
        if cleanup_task is not None:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
        close_result = mongo_client.close()
        if inspect.isawaitable(close_result):
            await close_result
        await redis_client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    allowed_origins = ["http://localhost:8000", "http://localhost:5500"]
    public_app_origin = settings.public_app_url.rstrip("/")
    if public_app_origin not in allowed_origins:
        allowed_origins.append(public_app_origin)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(access_qr_router)
    application.include_router(health_router, prefix=settings.api_prefix)
    application.include_router(auth_router, prefix=settings.api_prefix)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    application.mount("/media", StaticFiles(directory=settings.upload_dir), name="media")
    application.include_router(images_router, prefix=settings.api_prefix)
    application.include_router(audio_router, prefix=settings.api_prefix)
    application.include_router(translations_router, prefix=settings.api_prefix)
    application.include_router(translation_preview_router, prefix=settings.api_prefix)
    application.include_router(presence_router, prefix=settings.api_prefix)
    application.include_router(root_websocket_router)
    application.include_router(heatmap_router, prefix=settings.api_prefix)
    application.include_router(admin_accounts_router, prefix=settings.api_prefix)
    application.include_router(analytics_router, prefix=settings.api_prefix)
    application.include_router(public_poi_router, prefix=settings.api_prefix)
    application.include_router(admin_poi_router, prefix=settings.api_prefix)
    dashboard_dir = Path(__file__).resolve().parents[2] / "admin-dashboard"
    experimental_tourist_dir = Path(__file__).resolve().parents[2] / "tourist-pwa"
    application.mount(
        "/experimental-tourist",
        StaticFiles(directory=experimental_tourist_dir, html=True),
        name="experimental-tourist",
    )
    application.mount("/", StaticFiles(directory=dashboard_dir, html=True), name="web")
    return application


app = create_app()
