import asyncio
from datetime import date

from fastapi.testclient import TestClient

from app.services.auth import hash_password


def prepare_visit_test(client: TestClient) -> str:
    database = client.app.state.test_database
    asyncio.run(
        database.admins.insert_one(
            {
                "email": "visit-owner@example.com",
                "display_name": "POI owner",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password("visit-owner-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "visit-owner@example.com", "password": "visit-owner-password"},
    )
    response = client.post(
        "/api/admin/pois",
        json={
            "name": "Visit-log POI",
            "coordinates": {"latitude": 10.0, "longitude": 106.0},
            "geofence_radius_m": 30,
            "category": "heritage",
            "content": {"vi": "Original narration.", "en": "English narration."},
        },
    )
    assert response.status_code == 201
    client.post("/api/auth/logout")
    asyncio.run(
        database.admins.insert_one(
            {
                "email": "visit-analyst@example.com",
                "display_name": "Visit analyst",
                "role": "analytics_viewer",
                "is_active": True,
                "password_hash": hash_password("visit-analyst-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "visit-analyst@example.com", "password": "visit-analyst-password"},
    )
    return response.json()["id"]


def test_connection_entry_and_exit_events_feed_analytics(client: TestClient) -> None:
    poi_id = prepare_visit_test(client)
    database = client.app.state.test_database

    with client.websocket_connect("/api/ws/visitors?language=en") as visitor:
        connected = visitor.receive_json()
        visitor_id = connected["visitor_id"]
        assert connected["language"] == "en"

        visitor.send_json(
            {
                "type": "heartbeat",
                "poi_id": poi_id,
                "latitude": 10.0,
                "longitude": 106.0,
            }
        )
        assert visitor.receive_json()["type"] == "heartbeat_ack"

        visitor.send_json({"type": "heartbeat", "poi_id": None})
        assert visitor.receive_json()["type"] == "heartbeat_ack"

    events = asyncio.run(
        database.visits.find({"visitor_id": visitor_id}).sort("created_at", 1).to_list(length=10)
    )
    assert [event["event_type"] for event in events] == [
        "visitor_connect",
        "poi_enter",
        "poi_leave",
    ]
    assert events[0]["latitude"] == 10.0
    assert events[0]["longitude"] == 106.0
    assert events[1]["poi_id"] == events[2]["poi_id"]

    report = client.get(
        "/api/admin/reports",
        params={"start_date": date.today().isoformat(), "end_date": date.today().isoformat()},
    )
    assert report.status_code == 200
    assert report.json()["total_visits"] == 1
    assert report.json()["by_poi"][0]["poi_id"] == poi_id
    assert report.json()["by_language"][0]["language"] == "en"


def test_invalid_poi_entry_is_not_logged(client: TestClient) -> None:
    with client.websocket_connect("/api/ws/visitors") as visitor:
        visitor.receive_json()
        visitor.send_json({"type": "heartbeat", "poi_id": "invalid"})
        error = visitor.receive_json()
        assert error["type"] == "error"

    events = asyncio.run(client.app.state.test_database.visits.find({}).to_list(length=10))
    assert len(events) == 1
    assert events[0]["event_type"] == "visitor_connect"
