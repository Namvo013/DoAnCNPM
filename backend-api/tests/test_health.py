from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import get_database, get_redis
from app.main import create_app


def test_health_reports_sql_server_and_redis(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "sql_server": "ok", "redis": "ok"}


def test_health_reports_unavailable_dependencies() -> None:
    class UnavailableDatabase:
        async def execute(self, query: object) -> None:
            raise ConnectionError("SQL Server is down")

    class UnavailableRedis:
        async def ping(self) -> None:
            raise ConnectionError("Redis is down")

    application = create_app()
    application.state.database_engine = create_async_engine("sqlite+aiosqlite://")
    application.state.redis = FakeRedis(decode_responses=True)
    application.dependency_overrides[get_database] = lambda: UnavailableDatabase()
    application.dependency_overrides[get_redis] = lambda: UnavailableRedis()
    with TestClient(application) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "unavailable",
        "sql_server": "unavailable",
        "redis": "unavailable",
    }
