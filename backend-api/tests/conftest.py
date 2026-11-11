import os
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.config import get_settings
from app.database import get_database, get_redis, get_websocket_database, get_websocket_redis
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    monkeypatch.setattr(get_settings(), "environment", "development")
    application = create_app()
    mongo_client = AsyncMongoMockClient()
    database = mongo_client["test"]
    redis = FakeRedis(decode_responses=True)
    application.state.test_database = database
    application.state.test_redis = redis
    application.state.disable_background_tasks = True
    application.dependency_overrides[get_database] = lambda: database
    application.dependency_overrides[get_redis] = lambda: redis
    application.dependency_overrides[get_websocket_database] = lambda: database
    application.dependency_overrides[get_websocket_redis] = lambda: redis
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()
    mongo_client.close()
