import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.routers.audio import audio_service
from app.services.auth import hash_password

MP3_BYTES = b"\xff\xfb\x90\x64" + b"\0" * 32


def create_poi(client: TestClient, role: str = "super_admin") -> str:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "audio-admin@example.com",
                "display_name": "Audio admin",
                "role": role,
                "is_active": True,
                "password_hash": hash_password("audio-test-password"),
            }
        )
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": "audio-admin@example.com", "password": "audio-test-password"},
    )
    assert login_response.status_code == 200
    response = client.post(
        "/api/admin/pois",
        json={
            "name": "Test POI",
            "coordinates": {"latitude": 10, "longitude": 106},
            "geofence_radius_m": 20,
            "category": "park",
            "content": {"vi": "Nội dung thuyết minh"},
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_admin_uploads_mp3_and_guest_can_fetch_audio(
    client: TestClient,
) -> None:
    poi_id = create_poi(client)

    response = client.post(
        f"/api/admin/pois/{poi_id}/audio/vi/upload",
        files={"file": ("voice.mp3", MP3_BYTES, "audio/mpeg")},
    )

    assert response.status_code == 200
    audio_url = response.json()["audio_url"]
    assert client.get(audio_url).content == MP3_BYTES
    poi = client.get(f"/api/pois/{poi_id}").json()
    assert poi["audio"]["vi"] == audio_url


def test_audio_upload_rejects_non_mp3_and_files_over_20_mb(client: TestClient) -> None:
    poi_id = create_poi(client)
    invalid = client.post(
        f"/api/admin/pois/{poi_id}/audio/vi/upload",
        files={"file": ("fake.mp3", b"not an mp3 file", "audio/mpeg")},
    )
    assert invalid.status_code == 415

    oversized = client.post(
        f"/api/admin/pois/{poi_id}/audio/vi/upload",
        files={"file": ("large.mp3", MP3_BYTES + b"x" * (20 * 1024 * 1024), "audio/mpeg")},
    )
    assert oversized.status_code == 413


def test_audio_generation_uses_requested_language_and_voice(
    client: TestClient,
    monkeypatch,
) -> None:
    poi_id = create_poi(client)

    class FakeCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text
            self.voice = voice

        async def save(self, path: str) -> None:
            await asyncio.to_thread(Path(path).write_bytes, MP3_BYTES)

    monkeypatch.setattr("app.services.audio.edge_tts.Communicate", FakeCommunicate)
    response = client.post(f"/api/admin/pois/{poi_id}/audio/vi/generate")

    assert response.status_code == 200
    assert response.json()["voice"] == "vi-VN-HoaiMyNeural"


def test_content_editor_can_generate_audio_but_guest_cannot(
    client: TestClient,
    monkeypatch,
) -> None:
    poi_id = create_poi(client)
    client.post("/api/auth/logout")
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "editor@example.com",
                "display_name": "Content editor",
                "role": "content_editor",
                "is_active": True,
                "password_hash": hash_password("editor-test-password"),
            }
        )
    )
    client.post(
        "/api/auth/login",
        json={"email": "editor@example.com", "password": "editor-test-password"},
    )

    class FakeCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            self.text = text
            self.voice = voice

        async def save(self, path: str) -> None:
            await asyncio.to_thread(Path(path).write_bytes, MP3_BYTES)

    monkeypatch.setattr("app.services.audio.edge_tts.Communicate", FakeCommunicate)
    allowed = client.post(f"/api/admin/pois/{poi_id}/audio/vi/generate")
    assert allowed.status_code == 200

    client.post("/api/auth/logout")

    response = client.post(f"/api/admin/pois/{poi_id}/audio/vi/generate")

    assert response.status_code == 401
