from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

from app.config import get_settings
from app.gateway import (
    InternalServiceAccessMiddleware,
    _proxy_response,
    create_gateway_router,
    service_for_path,
)
from app.database import Base
from app.main import create_app, wait_for_schema
from sqlalchemy.ext.asyncio import create_async_engine


def _paths(service_role: str) -> set[str]:
    application = create_app(service_role)
    return {getattr(route, "path", "") for route in application.routes}


def test_service_roles_expose_only_their_domain_routes() -> None:
    auth_paths = _paths("auth")
    poi_paths = _paths("poi")
    presence_paths = _paths("presence")

    assert "/api/auth/login" in auth_paths
    assert "/api/admin/admins" in auth_paths
    assert "/api/pois" not in auth_paths
    assert "/api/pois" in poi_paths
    assert "/api/admin/pois" in poi_paths
    assert "/api/auth/login" not in poi_paths
    assert "/api/ws/tourist" in presence_paths
    assert "/api/admin/heatmap" in presence_paths
    assert "/api/pois" not in presence_paths
    assert "/api/admin/admins" not in presence_paths
    assert "/api/admin/reports" not in presence_paths


def test_gateway_retains_public_api_routes_and_forwards_domains() -> None:
    paths = _paths("gateway")

    assert "/api/health" in paths
    assert "/api/{path:path}" in paths
    assert "/api/admin/reports" in paths
    assert "/media/{path:path}" in paths
    assert "/login.html" not in paths


def test_gateway_routes_each_domain_to_the_expected_service() -> None:
    assert service_for_path("auth/login") == "auth"
    assert service_for_path("admin/admins") == "auth"
    assert service_for_path("pois") == "poi"
    assert service_for_path("admin/pois/poi-id/audio/vi/generate") == "poi"
    assert service_for_path("admin/images") == "poi"
    assert service_for_path("admin/translations/preview") == "poi"
    assert service_for_path("admin/heatmap") == "presence"
    assert service_for_path("admin/reports") is None
    assert service_for_path("admin/reports/visits") is None


def test_gateway_forwards_api_requests_and_preserves_cookies(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_service_url", "http://auth-service:8000")
    monkeypatch.setattr(settings, "internal_service_token", "test-internal-token")
    upstream = httpx.Response(
        200,
        headers=[
            ("content-type", "application/json"),
            ("set-cookie", "admin_session=first; HttpOnly"),
            ("set-cookie", "locale=vi; Path=/"),
        ],
        content=b'{"ok":true}',
    )
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            assert timeout == 30.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, headers, content):
            captured.update(method=method, url=url, headers=headers, content=content)
            return upstream

    monkeypatch.setattr("app.gateway.httpx.AsyncClient", FakeAsyncClient)
    application = FastAPI()
    application.include_router(create_gateway_router(settings))

    with TestClient(application) as client:
        response = client.post(
            "/api/auth/login?source=dashboard",
            headers={"cookie": "old_session=1"},
            json={"email": "admin@example.com"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(response.headers.get_list("set-cookie")) == 2
    assert captured["method"] == "POST"
    assert captured["url"] == "http://auth-service:8000/api/auth/login?source=dashboard"
    forwarded_headers = dict(captured["headers"])
    assert forwarded_headers["cookie"] == "old_session=1"
    assert forwarded_headers["X-Internal-Service-Token"] == "test-internal-token"


def test_internal_services_reject_requests_without_shared_token() -> None:
    application = FastAPI()
    application.add_middleware(InternalServiceAccessMiddleware, token="expected-token")

    @application.get("/api/private")
    async def private_endpoint() -> dict[str, bool]:
        return {"ok": True}

    @application.get("/api/health")
    async def health_endpoint() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(application) as client:
        denied = client.get("/api/private")
        allowed = client.get(
            "/api/private",
            headers={"X-Internal-Service-Token": "expected-token"},
        )
        health = client.get("/api/health")

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert health.status_code == 200


def test_gateway_rewrites_internal_service_redirects() -> None:
    upstream = httpx.Response(
        307,
        headers={"location": "http://poi-service:8000/api/pois"},
        content=b"",
    )

    response = _proxy_response(upstream, "http://poi-service:8000")

    assert response.status_code == 307
    assert response.headers["location"] == "/api/pois"


async def test_services_can_wait_for_auth_schema_initialization() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await wait_for_schema(engine)
    finally:
        await engine.dispose()
