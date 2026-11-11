from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_demo_mode_seeds_admin_and_supports_cookie_login(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "admin_seed_email", "admin@example.com")
    monkeypatch.setattr(settings, "admin_seed_password", "admin123")
    application = create_app()

    with TestClient(application) as client:
        health = client.get("/api/health")
        login = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        me = client.get("/api/auth/me")

        assert health.status_code == 200
        assert login.status_code == 200
        assert login.json()["role"] == "super_admin"
        assert "password_hash" not in login.json()
        assert "admin_session" in login.cookies
        assert me.status_code == 200
        assert me.json()["email"] == "admin@example.com"
        assert client.get("/api/admin/pois").status_code == 200


def test_demo_mode_is_rejected_outside_development(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "environment", "production")

    try:
        with TestClient(create_app()):
            raise AssertionError("Production must not start with demo mode enabled")
    except RuntimeError as error:
        assert "only available" in str(error)
