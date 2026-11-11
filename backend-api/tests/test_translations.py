import asyncio

from fastapi.testclient import TestClient

from app.routers.translations import translation_service
from app.schemas.poi import SupportedLanguage
from app.services.auth import hash_password


def create_poi(client: TestClient) -> str:
    asyncio.run(
        client.app.state.test_database.admins.insert_one(
            {
                "email": "translator@example.com",
                "display_name": "Translator",
                "role": "super_admin",
                "is_active": True,
                "password_hash": hash_password("translator-password"),
            }
        )
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "translator@example.com", "password": "translator-password"},
    )
    assert login.status_code == 200
    response = client.post(
        "/api/admin/pois",
        json={
            "name": "Language test POI",
            "coordinates": {"latitude": 10, "longitude": 106},
            "geofence_radius_m": 25,
            "category": "heritage",
            "content": {"vi": "Nội dung gốc.", "en": "Published English content."},
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_translation_draft_edit_approval_and_public_fallback(
    client: TestClient,
    monkeypatch,
) -> None:
    poi_id = create_poi(client)

    async def fake_translate(text: str, language: SupportedLanguage) -> str:
        assert "Nội dung gốc." in text
        assert language == "ja"
        return "自動翻訳"

    monkeypatch.setattr(translation_service, "_translate_text", fake_translate)
    generated = client.post(f"/api/admin/pois/{poi_id}/translations/ja/generate")

    assert generated.status_code == 200
    assert generated.json()["status"] == "draft"
    edited = client.put(
        f"/api/admin/pois/{poi_id}/translations/ja",
        json={"text": "編集済みの日本語"},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "draft"

    hidden = client.get(f"/api/pois/{poi_id}?language=ja")
    assert hidden.status_code == 200
    assert hidden.json()["content_language"] == "en"
    assert hidden.json()["content"] == {"en": "Published English content."}

    approved = client.post(f"/api/admin/pois/{poi_id}/translations/ja/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "published"
    visible = client.get(f"/api/pois/{poi_id}?language=ja")
    assert visible.json()["content_language"] == "ja"
    assert visible.json()["content"] == {"ja": "編集済みの日本語"}


def test_translation_service_rejects_vietnamese_as_target(client: TestClient) -> None:
    poi_id = create_poi(client)

    response = client.post(f"/api/admin/pois/{poi_id}/translations/vi/generate")

    assert response.status_code == 422


def test_translation_preview_generates_all_supported_targets(
    client: TestClient,
    monkeypatch,
) -> None:
    create_poi(client)

    async def fake_translate(text: str, language: SupportedLanguage) -> str:
        assert text == "Nội dung mới."
        return f"translated-{language.value}"

    monkeypatch.setattr(translation_service, "_translate_text", fake_translate)
    response = client.post(
        "/api/admin/translations/preview",
        json={
            "text": " Nội dung mới. ",
            "target_languages": ["en", "ja", "ko", "zh"],
        },
    )

    assert response.status_code == 200
    assert response.json()["translations"] == {
        "en": "translated-en",
        "ja": "translated-ja",
        "ko": "translated-ko",
        "zh": "translated-zh",
    }


def test_translation_preview_requires_content_permission(client: TestClient) -> None:
    response = client.post(
        "/api/admin/translations/preview",
        json={"text": "Nội dung mới."},
    )

    assert response.status_code == 401


def test_translation_preview_falls_back_to_free_service_without_gemini_key(
    client: TestClient,
    monkeypatch,
) -> None:
    create_poi(client)
    monkeypatch.setattr(translation_service.settings, "gemini_api_key", "")
    monkeypatch.setattr(
        translation_service,
        "_translate_free",
        lambda text, language: f"free-{language.value}",
    )

    response = client.post(
        "/api/admin/translations/preview",
        json={"text": "Nội dung mới."},
    )

    assert response.status_code == 200
    assert response.json()["translations"] == {
        "en": "free-en",
        "ja": "free-ja",
        "ko": "free-ko",
        "zh": "free-zh",
    }
