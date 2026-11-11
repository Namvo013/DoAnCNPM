import asyncio
import time

from fastapi.testclient import TestClient

from app.routers.presence import presence_service
from app.services.auth import hash_password
from app.services.presence import PRESENCE_KEY, PRESENCE_POI_KEY, PresenceService


def test_visitor_websocket_heartbeats_and_disconnects(client: TestClient) -> None:
    with client.websocket_connect("/ws/tourist") as visitor:
        connected = visitor.receive_json()
        assert connected["type"] == "connected"
        assert connected["online"] == 1
        visitor.send_json({"type": "heartbeat"})
        heartbeat = visitor.receive_json()
        assert heartbeat == {"type": "heartbeat_ack", "online": 1}

    online = asyncio.run(presence_service.online_count(client.app.state.test_redis))
    assert online == 0


def test_admin_websocket_receives_immediate_presence_updates(client: TestClient) -> None:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "presence-admin@example.com",
                "display_name": "Presence admin",
                "role": "analytics_viewer",
                "is_active": True,
                "password_hash": hash_password("presence-test-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "presence-admin@example.com", "password": "presence-test-password"},
    )

    with client.websocket_connect("/ws/admin") as admin_socket:
        assert admin_socket.receive_json() == {"type": "presence", "online": 0, "poi_counts": []}
        with client.websocket_connect("/ws/tourist") as visitor_socket:
            assert visitor_socket.receive_json()["online"] == 1
            update = admin_socket.receive_json()
            assert update == {"type": "presence", "online": 1, "poi_counts": []}


def test_stale_visitor_is_removed_after_45_seconds(client: TestClient) -> None:
    redis = client.app.state.test_redis
    asyncio.run(redis.zadd(PRESENCE_KEY, {"stale-visitor": time.time() - 46}))

    assert asyncio.run(presence_service.online_count(redis)) == 0
    assert asyncio.run(redis.zcard(PRESENCE_KEY)) == 0


def test_presence_snapshot_counts_visitors_per_poi_and_warns_above_50(client: TestClient) -> None:
    redis = client.app.state.test_redis
    visitors = {f"visitor-{index}": time.time() for index in range(51)}
    asyncio.run(redis.zadd(PRESENCE_KEY, visitors))
    asyncio.run(
        redis.hset(
            PRESENCE_POI_KEY,
            mapping={visitor_id: "poi-123" for visitor_id in visitors},
        )
    )

    snapshot = asyncio.run(PresenceService().snapshot(redis))

    assert snapshot["online"] == 51
    assert snapshot["poi_counts"] == [
        {"poi_id": "poi-123", "visitor_count": 51, "warning": True}
    ]
