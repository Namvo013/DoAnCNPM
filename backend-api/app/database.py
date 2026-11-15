import re
import secrets
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request, WebSocket, status
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=lambda: secrets.token_hex(12))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class POI(Base):
    __tablename__ = "pois"
    __table_args__ = (
        Index("ix_pois_is_active_parent", "is_active", "parent_poi_id"),
        Index("ix_pois_latitude_longitude", "latitude", "longitude"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=lambda: secrets.token_hex(12))
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geofence_radius_m: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    category: Mapped[str] = mapped_column(String(100))
    content: Mapped[dict[str, str]] = mapped_column(JSON)
    published_content: Mapped[dict[str, str]] = mapped_column(JSON)
    name_translations: Mapped[dict[str, str]] = mapped_column(JSON)
    category_translations: Mapped[dict[str, str]] = mapped_column(JSON)
    audio: Mapped[dict[str, str]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_poi_id: Mapped[str | None] = mapped_column(
        String(24), ForeignKey("pois.id", ondelete="NO ACTION"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Translation(Base):
    __tablename__ = "translations"
    __table_args__ = (
        UniqueConstraint("poi_id", "language", name="uq_translation_poi_language"),
        Index("ix_translations_poi_id", "poi_id"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=lambda: secrets.token_hex(12))
    poi_id: Mapped[str] = mapped_column(String(24), ForeignKey("pois.id", ondelete="CASCADE"))
    language: Mapped[str] = mapped_column(String(8))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (
        Index("ix_visits_event_created", "event_type", "created_at"),
        Index("ix_visits_poi_created", "poi_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(24), primary_key=True, default=lambda: secrets.token_hex(12))
    visitor_id: Mapped[str] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(32))
    poi_id: Mapped[str | None] = mapped_column(
        String(24), ForeignKey("pois.id", ondelete="SET NULL"), nullable=True
    )
    source_poi_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    language: Mapped[str] = mapped_column(String(8))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VisitorLocation(Base):
    __tablename__ = "visitor_locations"

    visitor_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def parse_id(value: str) -> str | None:
    return value.lower() if re.fullmatch(r"[0-9a-fA-F]{24}", value) else None


def poi_document(poi: POI) -> dict[str, Any]:
    return {
        "_id": poi.id,
        "name": poi.name,
        "location": {
            "type": "Point",
            "coordinates": [poi.longitude, poi.latitude],
        },
        "geofence_radius_m": poi.geofence_radius_m,
        "image_url": poi.image_url,
        "category": poi.category,
        "content": poi.content or {},
        "published_content": poi.published_content or {},
        "name_translations": poi.name_translations or {},
        "category_translations": poi.category_translations or {},
        "audio": poi.audio or {},
        "is_active": poi.is_active,
        "parent_poi_id": poi.parent_poi_id,
        "created_at": poi.created_at,
        "updated_at": poi.updated_at,
    }


def admin_document(admin: Admin) -> dict[str, Any]:
    return {
        "_id": admin.id,
        "email": admin.email,
        "display_name": admin.display_name,
        "role": admin.role,
        "is_active": admin.is_active,
        "password_hash": admin.password_hash,
        "created_at": admin.created_at,
        "updated_at": admin.updated_at,
    }


def translation_document(translation: Translation) -> dict[str, Any]:
    return {
        "_id": translation.id,
        "poi_id": translation.poi_id,
        "language": translation.language,
        "text": translation.text,
        "status": translation.status,
        "created_at": translation.created_at,
        "updated_at": translation.updated_at,
        "published_at": translation.published_at,
    }


async def get_database(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable")
    async with session_factory() as session:
        yield session


async def get_redis(request: Request) -> AsyncIterator[Any]:
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis is unavailable")
    yield redis_client


async def get_websocket_database(websocket: WebSocket) -> AsyncIterator[AsyncSession]:
    session_factory = getattr(websocket.app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable")
    async with session_factory() as session:
        yield session


async def get_websocket_redis(websocket: WebSocket) -> AsyncIterator[Any]:
    redis_client = getattr(websocket.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis is unavailable")
    yield redis_client
