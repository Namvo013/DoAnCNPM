import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from bson import ObjectId
from fastapi import HTTPException, status

from app.config import Settings, get_settings
from app.schemas.poi import SupportedLanguage
from app.schemas.translations import TARGET_LANGUAGES, TranslationStatus

FREE_TARGETS: dict[SupportedLanguage, tuple[str, str]] = {
    SupportedLanguage.EN: ("en", "en-GB"),
    SupportedLanguage.JA: ("ja", "ja-JP"),
    SupportedLanguage.KO: ("ko", "ko-KR"),
    SupportedLanguage.ZH: ("zh-CN", "zh-CN"),
}


def split_text(text: str, limit: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        while len(paragraph) > limit:
            chunks.append(paragraph[:limit])
            paragraph = paragraph[limit:]
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def translation_response(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "poi_id": str(document["poi_id"]),
        "language": document["language"],
        "text": document["text"],
        "status": document["status"],
        "created_at": document["created_at"].isoformat(),
        "updated_at": document["updated_at"].isoformat(),
        "published_at": document["published_at"].isoformat() if document.get("published_at") else None,
    }


class TranslationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def generate(self, database: Any, poi_id: str, language: SupportedLanguage) -> dict[str, Any]:
        if language is SupportedLanguage.VI:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Vietnamese is the source language and cannot be translated to itself",
            )
        poi = await self._find_poi(database, poi_id)
        source_text = poi.get("content", {}).get("vi", "")
        if not source_text.strip():
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vietnamese content is required")
        translated = await self._translate_text(source_text, language)
        return await self._save_draft(database, poi["_id"], language, translated)

    async def preview_all(
        self,
        source_text: str,
        target_languages: list[SupportedLanguage] | None = None,
    ) -> dict[str, str]:
        text = source_text.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Vietnamese content is required",
            )
        languages = target_languages or list(TARGET_LANGUAGES)
        translations = await asyncio.gather(
            *(self._translate_text(text, language) for language in languages)
        )
        return {language.value: translated for language, translated in zip(languages, translations)}

    async def update(
        self,
        database: Any,
        poi_id: str,
        language: SupportedLanguage,
        text: str,
    ) -> dict[str, Any]:
        if language is SupportedLanguage.VI:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Vietnamese is the source language and cannot be edited as a translation",
            )
        poi = await self._find_poi(database, poi_id)
        return await self._save_draft(database, poi["_id"], language, text)

    async def get(self, database: Any, poi_id: str, language: SupportedLanguage) -> dict[str, Any]:
        poi = await self._find_poi(database, poi_id)
        translation = await database.translations.find_one(
            {"poi_id": poi["_id"], "language": language.value}
        )
        if translation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")
        return translation_response(translation)

    async def approve(self, database: Any, poi_id: str, language: SupportedLanguage) -> dict[str, Any]:
        if language is SupportedLanguage.VI:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Vietnamese is the source language and cannot be approved as a translation",
            )
        poi = await self._find_poi(database, poi_id)
        translation = await database.translations.find_one(
            {"poi_id": poi["_id"], "language": language.value}
        )
        if translation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")
        now = datetime.now(timezone.utc)
        await database.translations.update_one(
            {"_id": translation["_id"]},
            {"$set": {"status": TranslationStatus.PUBLISHED.value, "published_at": now, "updated_at": now}},
        )
        result = await database.pois.update_one(
            {"_id": poi["_id"]},
            {"$set": {f"published_content.{language.value}": translation["text"], "updated_at": now}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        translation.update({"status": TranslationStatus.PUBLISHED.value, "published_at": now, "updated_at": now})
        return translation_response(translation)

    async def _translate_text(self, text: str, language: SupportedLanguage) -> str:
        if not any(character.isalpha() for character in text):
            # Mã số/ký tự (vd danh mục "01") không cần dịch và dễ bị dịch sai.
            return text
        if self.settings.gemini_api_key:
            return await self._translate_with_gemini(text, language)
        if language not in FREE_TARGETS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only non-Vietnamese languages can be translated",
            )
        return await asyncio.to_thread(self._translate_free, text, language)

    def _translate_free(self, text: str, language: SupportedLanguage) -> str:
        from deep_translator import GoogleTranslator, MyMemoryTranslator

        google_code, memory_code = FREE_TARGETS[language]
        providers = (
            (lambda: GoogleTranslator(source="vi", target=google_code), 4500),
            (lambda: MyMemoryTranslator(source="vi-VN", target=memory_code), 450),
        )
        last_error: Exception | None = None
        for build_translator, limit in providers:
            try:
                translator = build_translator()
                parts: list[str] = []
                for chunk in split_text(text, limit):
                    translated = translator.translate(chunk)
                    if not translated or not translated.strip():
                        raise ValueError("Empty translation result")
                    parts.append(translated.strip())
                return "\n\n".join(parts)
            except Exception as error:  # noqa: BLE001 - thử nhà cung cấp kế tiếp
                last_error = error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Free translation service failed",
        ) from last_error

    async def _translate_with_gemini(self, text: str, language: SupportedLanguage) -> str:
        target_language = {
            SupportedLanguage.EN: "English, using natural and grammatically correct English",
            SupportedLanguage.JA: "Japanese, using natural modern Japanese and Japanese writing",
            SupportedLanguage.KO: "Korean, using natural Korean written in Hangul",
            SupportedLanguage.ZH: "Simplified Chinese, using natural Mandarin Chinese in Simplified Chinese characters",
            SupportedLanguage.VI: "Vietnamese",
        }[language]
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Translate the following Vietnamese tourist-audio-guide text into "
                                f"{target_language}. The result must be entirely in the target language "
                                "and use its correct writing system. Preserve the original meaning, "
                                "place and person names, and paragraph breaks. Do not add explanations, "
                                f"labels, or text in another language. Return only the translation.\n\n{text}"
                            )
                        }
                    ]
                }
            ]
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers={"x-goog-api-key": self.settings.gemini_api_key}, json=payload)
                response.raise_for_status()
                body = response.json()
                translated = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        except httpx.HTTPError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini translation request failed",
            ) from error
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an invalid translation response",
            ) from error
        if not translated:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Gemini returned an empty translation",
            )
        return translated

    async def _save_draft(
        self,
        database: Any,
        poi_id: ObjectId,
        language: SupportedLanguage,
        text: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        await database.translations.update_one(
            {"poi_id": poi_id, "language": language.value},
            {
                "$set": {
                    "text": text,
                    "status": TranslationStatus.DRAFT.value,
                    "updated_at": now,
                    "published_at": None,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        document = await database.translations.find_one(
            {"poi_id": poi_id, "language": language.value}
        )
        return translation_response(document)

    async def _find_poi(self, database: Any, poi_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(poi_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        document = await database.pois.find_one({"_id": ObjectId(poi_id)})
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        return document
