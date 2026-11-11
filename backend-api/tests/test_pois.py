import asyncio

from bson import ObjectId
from fastapi.testclient import TestClient

from app.services.pois import PoiService
from app.services.auth import hash_password


POI_PAYLOAD = {
    "name": "Bến Nhà Rồng",
    "coordinates": {"latitude": 10.7685, "longitude": 106.706},
    "geofence_radius_m": 50,
    "image_url": "https://example.org/poi.jpg",
    "category": "museum",
    "content": {"vi": "Bảo tàng và di tích lịch sử."},
}


def login_as(client: TestClient, role: str = "super_admin") -> None:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "poi-admin@example.com",
                "display_name": "POI admin",
                "role": role,
                "is_active": True,
                "password_hash": hash_password("poi-test-password"),
            }
        )
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "poi-admin@example.com", "password": "poi-test-password"},
    )
    assert response.status_code == 200


def test_admin_can_create_update_and_delete_poi(client: TestClient) -> None:
    login_as(client)
    created = client.post("/api/admin/pois", json=POI_PAYLOAD)

    assert created.status_code == 201
    poi = created.json()
    assert poi["geofence_radius_m"] == 50
    assert poi["coordinates"]["latitude"] == 10.7685

    updated = client.put(f"/api/admin/pois/{poi['id']}", json={"name": "Updated museum"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated museum"

    deleted = client.delete(f"/api/admin/pois/{poi['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/pois/{poi['id']}").status_code == 404


def test_admin_poi_list_includes_inactive_records_and_supports_pagination(client: TestClient) -> None:
    login_as(client)
    created = client.post("/api/admin/pois", json=POI_PAYLOAD)
    poi_id = created.json()["id"]
    assert client.put(f"/api/admin/pois/{poi_id}", json={"is_active": False}).status_code == 200

    response = client.get("/api/admin/pois?limit=1&skip=0")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["is_active"] is False


def test_poi_requires_vietnamese_and_valid_geofence(client: TestClient) -> None:
    login_as(client)
    no_vietnamese = {**POI_PAYLOAD, "content": {"en": "English content"}}
    assert client.post("/api/admin/pois", json=no_vietnamese).status_code == 422

    invalid_radius = {**POI_PAYLOAD, "geofence_radius_m": 1001}
    assert client.post("/api/admin/pois", json=invalid_radius).status_code == 422


def test_poi_geofence_radius_allows_1000_meters_for_create_and_update(client: TestClient) -> None:
    login_as(client)
    created = client.post(
        "/api/admin/pois",
        json={**POI_PAYLOAD, "geofence_radius_m": 1000},
    )

    assert created.status_code == 201
    poi_id = created.json()["id"]
    assert created.json()["geofence_radius_m"] == 1000

    updated = client.put(
        f"/api/admin/pois/{poi_id}",
        json={"geofence_radius_m": 1000},
    )

    assert updated.status_code == 200
    assert updated.json()["geofence_radius_m"] == 1000
    assert client.put(
        f"/api/admin/pois/{poi_id}",
        json={"geofence_radius_m": 1001},
    ).status_code == 422


def test_poi_hierarchy_is_not_supported(client: TestClient) -> None:
    login_as(client)
    destination_response = client.post("/api/admin/pois", json=POI_PAYLOAD)
    assert destination_response.status_code == 201
    destination = destination_response.json()
    artifact_create = client.post(
        "/api/admin/pois",
        json={**POI_PAYLOAD, "parent_poi_id": destination["id"]},
    )
    assert artifact_create.status_code == 422
    artifact_update = client.put(
        f"/api/admin/pois/{destination['id']}",
        json={"parent_poi_id": None},
    )
    assert artifact_update.status_code == 422
    assert client.get(f"/api/pois/{destination['id']}").json().get("parent_poi_id") is None
    assert client.delete(f"/api/admin/pois/{destination['id']}").status_code == 204


def test_legacy_child_pois_are_hidden_from_admin_and_public_lists(client: TestClient) -> None:
    login_as(client)
    created = client.post("/api/admin/pois", json=POI_PAYLOAD)
    assert created.status_code == 201
    root = asyncio.run(
        client.app.state.test_database.pois.find_one({"name": POI_PAYLOAD["name"]})
    )
    child_id = asyncio.run(
        client.app.state.test_database.pois.insert_one(
            {
                **root,
                "_id": ObjectId(),
                "name": "Legacy child",
                "parent_poi_id": root["_id"],
            }
        )
    ).inserted_id

    admin_list = client.get("/api/admin/pois")
    public_list = client.get("/api/pois")

    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1
    assert [item["name"] for item in admin_list.json()["items"]] == [POI_PAYLOAD["name"]]
    assert public_list.status_code == 200
    assert [item["name"] for item in public_list.json()["items"]] == [POI_PAYLOAD["name"]]
    assert client.get(f"/api/pois/{child_id}").status_code == 404


def test_poi_public_listing_and_role_denial(client: TestClient) -> None:
    login_as(client, role="analytics_viewer")
    denied = client.post("/api/admin/pois", json=POI_PAYLOAD)
    assert denied.status_code == 403

    assert client.get("/api/pois").status_code == 200
    assert client.get("/api/pois?latitude=10").status_code == 422


def test_public_poi_uses_translated_name_and_category_with_vietnamese_fallback(
    client: TestClient,
) -> None:
    login_as(client)
    created = client.post(
        "/api/admin/pois",
        json={
            **POI_PAYLOAD,
            "content": {"vi": "Nội dung tiếng Việt.", "ja": "日本語の内容。"},
            "name_translations": {"ja": "サイゴン大学"},
            "category_translations": {"ja": "大学"},
        },
    )
    assert created.status_code == 201
    poi_id = created.json()["id"]

    japanese = client.get(f"/api/pois/{poi_id}?language=ja")
    assert japanese.status_code == 200
    assert japanese.json()["name"] == "サイゴン大学"
    assert japanese.json()["category"] == "大学"

    korean = client.get(f"/api/pois/{poi_id}?language=ko")
    assert korean.status_code == 200
    assert korean.json()["name"] == POI_PAYLOAD["name"]
    assert korean.json()["category"] == POI_PAYLOAD["category"]


def test_poi_rejects_translations_for_unsupported_language(client: TestClient) -> None:
    login_as(client)
    response = client.post(
        "/api/admin/pois",
        json={**POI_PAYLOAD, "name_translations": {"fr": "Musée"}},
    )

    assert response.status_code == 422


def test_distance_search_uses_geo_near_filter() -> None:
    class Cursor:
        def limit(self, count: int) -> "Cursor":
            self.limit_count = count
            return self

        async def to_list(self, length: int) -> list[dict]:
            return []

    class Collection:
        def __init__(self) -> None:
            self.query = None
            self.index = None

        async def create_index(self, index: list[tuple[str, str]]) -> None:
            self.index = index

        def find(self, query: dict) -> Cursor:
            self.query = query
            return Cursor()

    class Database:
        def __init__(self) -> None:
            self.pois = Collection()

    database = Database()
    items = asyncio.run(PoiService().list_public(database, 20, 10.7, 106.6, 500))

    assert items == []
    assert database.pois.index == [("location", "2dsphere")]
    assert database.pois.query["location"]["$near"]["$geometry"]["coordinates"] == [106.6, 10.7]
    assert database.pois.query["location"]["$near"]["$maxDistance"] == 500
