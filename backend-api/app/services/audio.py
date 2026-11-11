import asyncio
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import edge_tts
from bson import ObjectId
from fastapi import HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.schemas.poi import SupportedLanguage

MAX_AUDIO_BYTES = 20 * 1024 * 1024
VOICES: dict[SupportedLanguage, str] = {
    SupportedLanguage.VI: "vi-VN-HoaiMyNeural",
    SupportedLanguage.EN: "en-US-JennyNeural",
    SupportedLanguage.JA: "ja-JP-NanamiNeural",
    SupportedLanguage.KO: "ko-KR-SunHiNeural",
    SupportedLanguage.ZH: "zh-CN-XiaoxiaoNeural",
}


def is_mp3(data: bytes) -> bool:
    offset = 0
    if data.startswith(b"ID3") and len(data) >= 10:
        size_bytes = data[6:10]
        if any(value & 0x80 for value in size_bytes):
            return False
        tag_size = sum(value << shift for value, shift in zip(size_bytes, (21, 14, 7, 0)))
        offset = 10 + tag_size + (10 if data[5] & 0x10 else 0)
    for position in range(offset, min(len(data) - 3, offset + 4096)):
        header = int.from_bytes(data[position : position + 4], "big")
        sync = header >> 21 == 0x7FF
        version = (header >> 19) & 0b11
        layer = (header >> 17) & 0b11
        bitrate_index = (header >> 12) & 0b1111
        sample_rate_index = (header >> 10) & 0b11
        if sync and version != 0b01 and layer != 0 and bitrate_index not in {0, 0b1111} and sample_rate_index != 0b11:
            return True
    return False


class AudioService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def generate(
        self,
        database: Any,
        poi_id: str,
        language: SupportedLanguage,
    ) -> dict[str, Any]:
        document = await self._find_poi(database, poi_id)
        text = document.get("content", {}).get(language.value)
        if not text or not text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"No {language.value} content is available for this POI",
            )
        voice = VOICES[language]
        filename = f"{poi_id}-{language.value}-{secrets.token_hex(8)}.mp3"
        destination = self._destination(filename)
        await edge_tts.Communicate(text, voice).save(str(destination))
        generated = await asyncio.to_thread(destination.read_bytes)
        if not is_mp3(generated):
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The speech service did not return valid MP3 audio",
            )
        audio_url = await self._save_track(database, document, language, filename)
        return {"poi_id": poi_id, "language": language.value, "audio_url": audio_url, "voice": voice}

    async def upload(
        self,
        database: Any,
        poi_id: str,
        language: SupportedLanguage,
        file: UploadFile,
    ) -> dict[str, Any]:
        data = await file.read(MAX_AUDIO_BYTES + 1)
        await file.close()
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="MP3 file exceeds 20 MB")
        if not is_mp3(data):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Uploaded file is not an MP3")
        document = await self._find_poi(database, poi_id)
        filename = f"{poi_id}-{language.value}-{secrets.token_hex(8)}.mp3"
        destination = self._destination(filename)
        await asyncio.to_thread(destination.write_bytes, data)
        audio_url = await self._save_track(database, document, language, filename)
        return {"poi_id": poi_id, "language": language.value, "audio_url": audio_url, "voice": None}

    async def _find_poi(self, database: Any, poi_id: str) -> dict[str, Any]:
        if not ObjectId.is_valid(poi_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        document = await database.pois.find_one({"_id": ObjectId(poi_id)})
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
        return document

    def _destination(self, filename: str) -> Path:
        directory = Path(self.settings.upload_dir).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        destination = (directory / filename).resolve()
        if destination.parent != directory:
            raise ValueError("Invalid media path")
        return destination

    async def _save_track(
        self,
        database: Any,
        document: dict[str, Any],
        language: SupportedLanguage,
        filename: str,
    ) -> str:
        audio_url = f"/media/{filename}"
        await database.pois.update_one(
            {"_id": document["_id"]},
            {
                "$set": {
                    f"audio.{language.value}": audio_url,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return audio_url
