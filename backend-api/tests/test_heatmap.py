import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.services.auth import hash_password


def create_test_poi(client: TestClient) -> str:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "heatmap-owner@example.com",
                "display_name": "Heatmap owner",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password("heatmap-owner-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "heatmap-owner@example.com", "password": "heatmap-owner-password"},
    )
    response = client.post(
        "/api/admin/pois",
        json={
            "name": "Crowded POI",
            "coordinates": {"latitude": 10.0, "longitude": 106.0},
            "geofence_radius_m": 100,
            "category": "park",
            "content": {"vi": "Visitor attraction."},
        },
    )
    assert response.status_code == 201
    client.post("/api/auth/logout")
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "heatmap-viewer@example.com",
                "display_name": "Analytics viewer",
                "role": "analytics_viewer",
                "is_active": True,
                "password_hash": hash_password("heatmap-viewer-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "heatmap-viewer@example.com", "password": "heatmap-viewer-password"},
    )
    return response.json()["id"]


def visitor_location(visitor_id: str, last_seen: datetime) -> dict:
    return {
        "visitor_id": visitor_id,
        "latitude": 10.0,
        "longitude": 106.0,
        "location": {"type": "Point", "coordinates": [106.0, 10.0]},
        "last_seen": last_seen,
    }


def test_guest_location_is_saved_and_included_in_heatmap(client: TestClient) -> None:
    poi_id = create_test_poi(client)

    with client.websocket_connect("/api/ws/visitors") as visitor:
        visitor.receive_json()
        visitor.send_json({"type": "heartbeat", "latitude": 10, "longitude": 106})
        visitor.receive_json()

        response = client.get("/api/admin/heatmap")
        assert response.status_code == 200
        heatmap = response.json()
        assert heatmap["located_visitors"] == 1
        assert heatmap["cells"][0]["count"] == 1
        assert heatmap["poi_crowds"][0]["poi_id"] == poi_id
        assert heatmap["poi_crowds"][0]["visitor_count"] == 1


def test_poi_crowd_warning_starts_only_above_50(client: TestClient) -> None:
    poi_id = create_test_poi(client)
    now = datetime.now(timezone.utc)
    collection = client.app.state.test_database.visitor_locations
    asyncio.run(collection.insert_many(visitor_location(f"visitor-{index}", now) for index in range(50)))

    at_threshold = client.get("/api/admin/heatmap").json()["poi_crowds"][0]
    assert at_threshold["poi_id"] == poi_id
    assert at_threshold["visitor_count"] == 50
    assert at_threshold["warning"] is False

    asyncio.run(collection.insert_one(visitor_location("visitor-50", now)))
    over_threshold = client.get("/api/admin/heatmap").json()["poi_crowds"][0]
    assert over_threshold["visitor_count"] == 51
    assert over_threshold["warning"] is True


def test_heatmap_excludes_locations_older_than_45_seconds(client: TestClient) -> None:
    create_test_poi(client)
    stale = datetime.now(timezone.utc) - timedelta(seconds=46)
    asyncio.run(
        client.app.state.test_database.visitor_locations.insert_one(
            visitor_location("stale-visitor", stale)
        )
    )

    response = client.get("/api/admin/heatmap")

    assert response.status_code == 200
    assert response.json()["located_visitors"] == 0
    assert response.json()["poi_crowds"][0]["warning"] is False
