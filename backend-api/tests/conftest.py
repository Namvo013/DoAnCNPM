import os
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.database import Admin, POI, Visit, VisitorLocation, admin_document, poi_document
from app.main import create_app


MODEL_BY_COLLECTION = {
    "admins": Admin,
    "pois": POI,
    "visits": Visit,
    "visitor_locations": VisitorLocation,
}


def _document(model: Any) -> dict[str, Any]:
    if isinstance(model, Admin):
        return admin_document(model)
    if isinstance(model, POI):
        return poi_document(model)
    if isinstance(model, Visit):
        return {
            "_id": model.id,
            "visitor_id": model.visitor_id,
            "event_type": model.event_type,
            "poi_id": model.poi_id,
            "language": model.language,
            "latitude": model.latitude,
            "longitude": model.longitude,
            "created_at": model.created_at,
        }
    return {
        "visitor_id": model.visitor_id,
        "latitude": model.latitude,
        "longitude": model.longitude,
        "last_seen": model.last_seen,
        "created_at": model.created_at,
    }


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == "$gte" and (actual is None or actual < value):
                    return False
                if operator == "$ne" and actual == value:
                    return False
        else:
            normalized = str(expected) if key == "_id" and expected is not None else expected
            if actual != normalized:
                return False
    return True


def _model(collection: str, document: dict[str, Any]) -> Any:
    values = dict(document)
    identifier = values.pop("_id", values.pop("id", None))
    if identifier is not None:
        values["id" if collection != "visitor_locations" else "visitor_id"] = str(identifier)
    if collection == "admins":
        values.setdefault("is_active", True)
        values.setdefault("created_at", datetime.now(timezone.utc))
    elif collection == "pois":
        location = values.pop("location", None)
        coordinates = location.get("coordinates", [0.0, 0.0]) if location else [0.0, 0.0]
        values["longitude"], values["latitude"] = coordinates
        if values.get("parent_poi_id") is not None:
            values["parent_poi_id"] = str(values["parent_poi_id"])
        values.setdefault("image_url", None)
        values.setdefault("category", "")
        values.setdefault("content", {})
        values.setdefault("published_content", values.get("content", {}))
        values.setdefault("name_translations", {})
        values.setdefault("category_translations", {})
        values.setdefault("audio", {})
        values.setdefault("is_active", True)
        values.setdefault("parent_poi_id", None)
        values.setdefault("created_at", datetime.now(timezone.utc))
        values.setdefault("updated_at", datetime.now(timezone.utc))
    elif collection == "visits":
        values.setdefault("visitor_id", "test-visitor")
        values.setdefault("event_type", "visitor_connect")
        values.setdefault("poi_id", None)
        values.setdefault("language", "vi")
        values.setdefault("latitude", None)
        values.setdefault("longitude", None)
        values.setdefault("created_at", datetime.now(timezone.utc))
        if values["poi_id"] is not None:
            values["poi_id"] = str(values["poi_id"])
    else:
        values.pop("location", None)
        values.setdefault("created_at", values.get("last_seen", datetime.now(timezone.utc)))
    return MODEL_BY_COLLECTION[collection](**values)


class TestCursor:
    def __init__(self, models: list[Any], collection: str) -> None:
        self.models = models
        self.collection = collection
        self.sort_field: str | None = None
        self.sort_direction = 1

    def sort(self, field: str, direction: int = 1) -> "TestCursor":
        self.sort_field = field
        self.sort_direction = direction
        return self

    async def to_list(self, length: int) -> list[dict[str, Any]]:
        documents = [_document(model) for model in self.models]
        if self.sort_field:
            documents.sort(
                key=lambda document: document.get(self.sort_field) or "",
                reverse=self.sort_direction < 0,
            )
        return documents[:length]


class TestCollection:
    def __init__(self, session_factory: Any, collection: str) -> None:
        self.session_factory = session_factory
        self.collection = collection
        self.model = MODEL_BY_COLLECTION[collection]

    async def insert_one(self, document: dict[str, Any]) -> SimpleNamespace:
        model = _model(self.collection, document)
        async with self.session_factory() as session:
            session.add(model)
            await session.commit()
            identifier = getattr(model, "id", getattr(model, "visitor_id", None))
            return SimpleNamespace(inserted_id=identifier)

    async def insert_many(self, documents: Any) -> SimpleNamespace:
        models = [_model(self.collection, document) for document in documents]
        async with self.session_factory() as session:
            session.add_all(models)
            await session.commit()
            identifiers = [
                getattr(model, "id", getattr(model, "visitor_id", None))
                for model in models
            ]
            return SimpleNamespace(inserted_ids=identifiers)

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            models = list(await session.scalars(select(self.model)))
        return next(
            (document for model in models if _matches(document := _document(model), query)),
            None,
        )

    def find(self, query: dict[str, Any]) -> TestCursor:
        async def load() -> list[Any]:
            async with self.session_factory() as session:
                models = list(await session.scalars(select(self.model)))
            return [model for model in models if _matches(_document(model), query)]

        return LazyTestCursor(load, self.collection)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> None:
        document = await self.find_one(query)
        if document is None:
            return
        key = document.get("_id", document.get("visitor_id"))
        async with self.session_factory() as session:
            model = await session.get(self.model, str(key))
            if model is not None:
                for name, value in update.get("$set", {}).items():
                    if name == "role" and self.collection == "admins":
                        setattr(model, name, value)
                    elif hasattr(model, name):
                        setattr(model, name, value)
                    elif self.collection == "visitor_locations" and name == "location":
                        continue
                await session.commit()


class LazyTestCursor:
    def __init__(self, loader: Any, collection: str) -> None:
        self.loader = loader
        self.collection = collection
        self.sort_field: str | None = None
        self.sort_direction = 1

    def sort(self, field: str, direction: int = 1) -> "LazyTestCursor":
        self.sort_field = field
        self.sort_direction = direction
        return self

    async def to_list(self, length: int) -> list[dict[str, Any]]:
        models = await self.loader()
        return await TestCursor(models, self.collection).sort(
            self.sort_field, self.sort_direction
        ).to_list(length) if self.sort_field else await TestCursor(models, self.collection).to_list(length)


class TestDatabase:
    def __init__(self, session_factory: Any) -> None:
        for collection in MODEL_BY_COLLECTION:
            setattr(self, collection, TestCollection(session_factory, collection))


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "environment", "development")
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        poolclass=NullPool,
    )
    application = create_app()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    application.state.database_engine = engine
    application.state.session_factory = session_factory
    application.state.test_database = TestDatabase(session_factory)
    application.state.redis = FakeRedis(decode_responses=True)
    application.state.test_redis = application.state.redis
    application.state.disable_background_tasks = True
    with TestClient(application) as test_client:
        yield test_client
