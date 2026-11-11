import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.services.auth import hash_password


def add_admin(client: TestClient, **overrides: object) -> None:
    admin = {
        "email": "admin@example.com",
        "display_name": "Site administrator",
        "role": "super_admin",
        "is_active": True,
        "password_hash": hash_password("correct-horse-battery"),
        "created_at": datetime.now(timezone.utc),
    }
    admin.update(overrides)
    asyncio.run(client.app.state.test_database.admins.insert_one(admin))


def test_login_sets_http_only_cookie_and_never_returns_password(client: TestClient) -> None:
    add_admin(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "ADMIN@example.com", "password": "correct-horse-battery"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    cookie = response.headers["set-cookie"]
    assert "admin_session=" in cookie
    assert "httponly" in cookie.lower()


def test_login_rejects_wrong_password_and_inactive_admin(client: TestClient) -> None:
    add_admin(client, is_active=False)
    wrong_password = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
    )
    assert wrong_password.status_code == 401

    inactive = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery"},
    )
    assert inactive.status_code == 401


def test_me_requires_login_and_logout_revokes_cookie(client: TestClient) -> None:
    add_admin(client)
    assert client.get("/api/auth/me").status_code == 401
    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "correct-horse-battery"},
    )
    assert login_response.status_code == 200

    assert client.get("/api/auth/me").status_code == 200
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert client.get("/api/auth/me").status_code == 401
