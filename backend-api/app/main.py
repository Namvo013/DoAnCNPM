import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from redis.exceptions import RedisError
from redis.asyncio import Redis
from sqlalchemy import Unicode, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Admin, Base, POI, Visitor, Visit, VisitorLocation
from app.gateway import InternalServiceAccessMiddleware, create_gateway_router
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


async def ensure_poi_unicode_columns(engine: AsyncEngine) -> None:
    if engine.dialect.name != "mssql":
        return

    async with engine.begin() as connection:
        def migrate(sync_connection: Connection) -> None:
            inspector = inspect(sync_connection)
            schema = inspector.default_schema_name
            columns = {
                column["name"]: column
                for column in inspector.get_columns("pois", schema=schema)
            }
            preparer = sync_connection.dialect.identifier_preparer
            table = (
                f"{preparer.quote_schema(schema)}.{preparer.quote(POI.__tablename__)}"
                if schema
                else preparer.quote(POI.__tablename__)
            )
            for name, length in (("name", 200), ("category", 100)):
                column = columns[name]
                if isinstance(column["type"], Unicode):
                    continue
                quoted_column = preparer.quote(name)
                nullable = "NULL" if column["nullable"] else "NOT NULL"
                sync_connection.exec_driver_sql(
                    f"ALTER TABLE {table} ALTER COLUMN {quoted_column} "
                    f"NVARCHAR({length}) {nullable}"
                )

        await connection.run_sync(migrate)


async def ensure_visitor_foreign_keys(engine: AsyncEngine) -> None:
    if engine.dialect.name != "mssql":
        return

    async with engine.begin() as connection:
        def migrate(sync_connection: Connection) -> None:
            inspector = inspect(sync_connection)
            schema = inspector.default_schema_name
            preparer = sync_connection.dialect.identifier_preparer

            def qualified(name: str) -> str:
                if schema:
                    return f"{preparer.quote_schema(schema)}.{preparer.quote(name)}"
                return preparer.quote(name)

            visitors_table = qualified(Visitor.__tablename__)
            visitor_sources = (
                (Visit.__tablename__, "created_at"),
                (VisitorLocation.__tablename__, "created_at"),
                (VisitorLocation.__tablename__, "last_seen"),
            )
            source_queries = [
                f"SELECT [visitor_id], [{timestamp_column}] AS [seen_at] "
                f"FROM {qualified(table_name)}"
                for table_name, timestamp_column in visitor_sources
                if inspector.has_table(table_name, schema=schema)
            ]
            if source_queries:
                union_query = " UNION ALL ".join(source_queries)
                sync_connection.exec_driver_sql(
                    f"""
                    INSERT INTO {visitors_table}
                        ([visitor_id], [first_seen], [last_seen], [disconnected_at])
                    SELECT source.[visitor_id], MIN(source.[seen_at]), MAX(source.[seen_at]), NULL
                    FROM ({union_query}) AS source
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {visitors_table} AS existing
                        WHERE existing.[visitor_id] = source.[visitor_id]
                    )
                    GROUP BY source.[visitor_id]
                    """
                )

            for table, column, constraint_name in (
                (Visit.__tablename__, "visitor_id", "fk_visits_visitor_id_visitors"),
                (
                    VisitorLocation.__tablename__,
                    "visitor_id",
                    "fk_visitor_locations_visitor_id_visitors",
                ),
            ):
                if not inspector.has_table(table, schema=schema):
                    continue
                foreign_keys = inspector.get_foreign_keys(table, schema=schema)
                if any(
                    foreign_key.get("referred_table") == Visitor.__tablename__
                    and foreign_key.get("constrained_columns") == [column]
                    and foreign_key.get("referred_columns") == ["visitor_id"]
                    for foreign_key in foreign_keys
                ):
                    continue
                sync_connection.exec_driver_sql(
                    f"ALTER TABLE {qualified(table)} WITH CHECK ADD CONSTRAINT "
                    f"{preparer.quote(constraint_name)} FOREIGN KEY "
                    f"({preparer.quote(column)}) REFERENCES {visitors_table} "
                    f"({preparer.quote('visitor_id')})"
                )

        await connection.run_sync(migrate)


async def wait_for_schema(engine: AsyncEngine) -> None:
    for attempt in range(30):
        async with engine.connect() as connection:
            def find_schema_issues(sync_connection: Connection) -> list[str]:
                inspector = inspect(sync_connection)
                issues = [
                    table.name
                    for table in Base.metadata.sorted_tables
                    if not inspector.has_table(table.name, schema=table.schema)
                ]
                if not issues:
                    for table, column in (
                        (Visit.__tablename__, "visitor_id"),
                        (VisitorLocation.__tablename__, "visitor_id"),
                    ):
                        foreign_keys = inspector.get_foreign_keys(
                            table,
                            schema=inspector.default_schema_name,
                        )
                        if not any(
                            foreign_key.get("referred_table") == Visitor.__tablename__
                            and foreign_key.get("constrained_columns") == [column]
                            and foreign_key.get("referred_columns") == ["visitor_id"]
                            for foreign_key in foreign_keys
                        ):
                            issues.append(f"{table}.{column} must reference visitors.visitor_id")
                if sync_connection.dialect.name == "mssql" and not issues:
                    poi_columns = {
                        column["name"]: column
                        for column in inspector.get_columns(
                            POI.__tablename__,
                            schema=inspector.default_schema_name,
                        )
                    }
                    issues.extend(
                        f"pois.{name} must use NVARCHAR"
                        for name in ("name", "category")
                        if not isinstance(poi_columns[name]["type"], Unicode)
                    )
                return issues

            schema_issues = await connection.run_sync(find_schema_issues)
        if not schema_issues:
            return
        if attempt < 29:
            await asyncio.sleep(1)
    raise RuntimeError(
        "Database schema is not ready; start the Auth service to initialize it. "
        f"Schema issues: {', '.join(schema_issues)}"
    )


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
    service_role = getattr(app.state, "service_role", "monolith")
    if service_role != "monolith" and settings.demo_mode:
        raise RuntimeError("DEMO_MODE is only supported by the monolith application")
    if service_role in {"auth", "poi", "presence"} and not settings.internal_service_token:
        raise RuntimeError("Set INTERNAL_SERVICE_TOKEN for independently running services")
    engine = getattr(app.state, "database_engine", None)
    if engine is None:
        if settings.demo_mode:
            if settings.environment.lower() != "development":
                raise RuntimeError("DEMO_MODE is only available when ENVIRONMENT=development")
            from fakeredis.aioredis import FakeRedis

            engine = create_async_engine("sqlite+aiosqlite://")
            redis_client = FakeRedis(decode_responses=True)
            logger.warning("DEMO_MODE enabled: using in-memory SQLite and Redis substitutes")
        else:
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            redis_client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                protocol=2,
            )
    else:
        redis_client = getattr(app.state, "redis", None)
        if redis_client is None:
            redis_client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                protocol=2,
            )
    app.state.database_engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.redis = redis_client
    if service_role in {"monolith", "auth"}:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await ensure_visitor_foreign_keys(engine)
        await ensure_poi_unicode_columns(engine)
    else:
        await wait_for_schema(engine)
    if settings.demo_mode and service_role == "monolith":
        async with app.state.session_factory() as session:
            admin = await session.scalar(select(Admin).where(Admin.email == settings.admin_seed_email.strip().lower()))
            if admin is None:
                session.add(
                    Admin(
                        email=settings.admin_seed_email.strip().lower(),
                        display_name="Admin nhóm 2",
                        role="super_admin",
                        is_active=True,
                        password_hash=hash_password(settings.admin_seed_password),
                        created_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()
    cleanup_task = None
    if service_role in {"monolith", "presence"} and not getattr(app.state, "disable_background_tasks", False):
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
        await engine.dispose()
        await redis_client.aclose()


def create_app(service_role: str | None = None) -> FastAPI:
    settings = get_settings()
    role = service_role or os.getenv("SERVICE_ROLE", "monolith")
    supported_roles = {"monolith", "gateway", "auth", "poi", "presence"}
    if role not in supported_roles:
        raise ValueError(f"SERVICE_ROLE must be one of: {', '.join(sorted(supported_roles))}")

    application = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    application.state.service_role = role
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
    if role in {"auth", "poi", "presence"}:
        application.add_middleware(
            InternalServiceAccessMiddleware,
            token=settings.internal_service_token,
        )

    if role in {"monolith", "gateway"}:
        application.include_router(access_qr_router)
    application.include_router(health_router, prefix=settings.api_prefix)

    if role in {"monolith", "auth"}:
        application.include_router(auth_router, prefix=settings.api_prefix)
        application.include_router(admin_accounts_router, prefix=settings.api_prefix)

    if role in {"monolith", "poi"}:
        application.include_router(images_router, prefix=settings.api_prefix)
        application.include_router(audio_router, prefix=settings.api_prefix)
        application.include_router(translations_router, prefix=settings.api_prefix)
        application.include_router(translation_preview_router, prefix=settings.api_prefix)
        application.include_router(public_poi_router, prefix=settings.api_prefix)
        application.include_router(admin_poi_router, prefix=settings.api_prefix)

    if role in {"monolith", "presence"}:
        application.include_router(presence_router, prefix=settings.api_prefix)
        application.include_router(root_websocket_router)
        application.include_router(heatmap_router, prefix=settings.api_prefix)

    if role in {"monolith", "gateway"}:
        application.include_router(analytics_router, prefix=settings.api_prefix)

    if role in {"monolith", "poi"}:
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        application.mount("/media", StaticFiles(directory=settings.upload_dir), name="media")

    if role == "gateway":
        application.include_router(create_gateway_router(settings))

    if role in {"monolith", "gateway"}:
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
