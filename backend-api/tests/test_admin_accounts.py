import asyncio

from fastapi.testclient import TestClient

from app.services.auth import hash_password


def login_super_admin(client: TestClient) -> str:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "root@example.com",
                "display_name": "Root",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password("root-account-password"),
            }
        )
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "root-account-password"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_super_admin_creates_updates_locks_and_deletes_staff(client: TestClient) -> None:
    login_super_admin(client)
    created = client.post(
        "/api/admin/admins",
        json={
            "email": "staff@example.com",
            "display_name": "Content staff",
            "role": "content_editor",
            "password": "initial-staff-password",
        },
    )

    assert created.status_code == 201
    assert created.json()["email"] == "staff@example.com"
    assert "password" not in created.json()
    assert "password_hash" not in created.json()
    staff_id = created.json()["id"]

    duplicate = client.post(
        "/api/admin/admins",
        json={
            "email": "staff@example.com",
            "display_name": "Duplicate",
            "role": "area_operator",
            "password": "duplicate-password",
        },
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        f"/api/admin/admins/{staff_id}",
        json={
            "email": "updated-staff@example.com",
            "display_name": "Updated staff",
            "role": "analytics_viewer",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "updated-staff@example.com"
    assert updated.json()["display_name"] == "Updated staff"
    assert updated.json()["role"] == "analytics_viewer"

    locked = client.patch(f"/api/admin/admins/{staff_id}", json={"is_active": False})
    assert locked.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"email": "updated-staff@example.com", "password": "initial-staff-password"},
    )
    assert login.status_code == 401

    client.post(
        "/api/auth/login",
        json={"email": "root@example.com", "password": "root-account-password"},
    )
    deleted = client.delete(f"/api/admin/admins/{staff_id}")
    assert deleted.status_code == 204


def test_super_admin_cannot_demote_or_delete_self(client: TestClient) -> None:
    admin_id = login_super_admin(client)

    demotion = client.patch(f"/api/admin/admins/{admin_id}", json={"role": "area_operator"})
    deletion = client.delete(f"/api/admin/admins/{admin_id}")
    lock = client.patch(f"/api/admin/admins/{admin_id}", json={"is_active": False})

    assert demotion.status_code == 403
    assert deletion.status_code == 403
    assert lock.status_code == 403


def test_admin_list_never_exposes_password_hash_and_requires_super_admin(client: TestClient) -> None:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "viewer@example.com",
                "display_name": "Viewer",
                "role": "analytics_viewer",
                "is_active": True,
                "password_hash": hash_password("viewer-account-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-account-password"},
    )
    assert client.get("/api/admin/admins").status_code == 403

    client.post(
        "/api/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-account-password"},
    )
    asyncio.run(
        client.app.state.test_database.admins.update_one(
            {"email": "viewer@example.com"},
            {"$set": {"role": "super_admin"}},
        )
    )
    new_login = client.post(
        "/api/auth/login",
        json={"email": "viewer@example.com", "password": "viewer-account-password"},
    )
    assert new_login.status_code == 200
    response = client.get("/api/admin/admins")
    assert response.status_code == 200
    assert "password_hash" not in response.text
