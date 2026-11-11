from fastapi.testclient import TestClient

from app.database import get_database, get_redis
from app.main import create_app


def test_health_reports_mongodb_and_redis(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mongodb": "ok", "redis": "ok"}


def test_health_reports_unavailable_dependencies() -> None:
    class UnavailableDatabase:
        async def command(self, name: str) -> None:
            raise ConnectionError("MongoDB is down")

    class UnavailableRedis:
        async def ping(self) -> None:
            raise ConnectionError("Redis is down")

    application = create_app()
    application.dependency_overrides[get_database] = lambda: UnavailableDatabase()
    application.dependency_overrides[get_redis] = lambda: UnavailableRedis()
    with TestClient(application) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "unavailable",
        "mongodb": "unavailable",
        "redis": "unavailable",
    }
