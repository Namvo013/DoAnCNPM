from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.authz import ROLE_PERMISSIONS, get_current_admin, require_permission, require_roles
from app.schemas.auth import AdminRole


def test_role_matrix_has_four_roles_and_super_admin_is_unrestricted() -> None:
    assert set(ROLE_PERMISSIONS) == set(AdminRole)
    assert len(AdminRole) == 4
    assert ROLE_PERMISSIONS[AdminRole.SUPER_ADMIN] == frozenset({"*"})


def test_role_guard_allows_permitted_roles_and_returns_403_for_others() -> None:
    application = FastAPI()
    application.dependency_overrides[get_current_admin] = lambda: {"role": "area_operator"}

    @application.get("/protected")
    async def protected(_: dict = Depends(require_roles(AdminRole.AREA_OPERATOR))):
        return {"ok": True}

    client = TestClient(application)
    assert client.get("/protected").status_code == 200

    application.dependency_overrides[get_current_admin] = lambda: {"role": "analytics_viewer"}
    forbidden = client.get("/protected")
    assert forbidden.status_code == 403


def test_permission_guard_denies_roles_without_permission() -> None:
    application = FastAPI()
    application.dependency_overrides[get_current_admin] = lambda: {"role": "content_editor"}

    @application.get("/analytics")
    async def analytics(_: dict = Depends(require_permission("analytics:read"))):
        return {"ok": True}

    response = TestClient(application).get("/analytics")

    assert response.status_code == 403
