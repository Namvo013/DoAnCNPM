from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile

from app.authz import require_permission
from app.database import get_database
from app.schemas.audio import AudioResponse
from app.schemas.poi import SupportedLanguage
from app.services.audio import AudioService

router = APIRouter(prefix="/admin/pois/{poi_id}/audio", tags=["admin audio"])
audio_service = AudioService()


@router.post("/{language}/generate", response_model=AudioResponse)
async def generate_audio(
    poi_id: str,
    language: SupportedLanguage,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> AudioResponse:
    return AudioResponse(**await audio_service.generate(database, poi_id, language))


@router.post("/{language}/upload", response_model=AudioResponse)
async def upload_audio(
    poi_id: str,
    language: SupportedLanguage,
    file: UploadFile = File(...),
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> AudioResponse:
    return AudioResponse(**await audio_service.upload(database, poi_id, language, file))
