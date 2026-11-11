from typing import Any

from fastapi import APIRouter, Depends

from app.authz import require_permission
from app.database import get_database
from app.schemas.poi import SupportedLanguage
from app.schemas.translations import (
    TranslationPreviewRequest,
    TranslationResponse,
    TranslationUpdate,
)
from app.services.translations import TranslationService

router = APIRouter(prefix="/admin/pois/{poi_id}/translations", tags=["admin translations"])
preview_router = APIRouter(prefix="/admin/translations", tags=["admin translations"])
translation_service = TranslationService()


@preview_router.post("/preview")
async def preview_translations(
    payload: TranslationPreviewRequest,
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> dict[str, dict[str, str]]:
    return {
        "translations": await translation_service.preview_all(
            payload.text,
            payload.target_languages,
        )
    }


@router.get("/{language}", response_model=TranslationResponse)
async def get_translation(
    poi_id: str,
    language: SupportedLanguage,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> TranslationResponse:
    return TranslationResponse(**await translation_service.get(database, poi_id, language))


@router.post("/{language}/generate", response_model=TranslationResponse)
async def generate_translation(
    poi_id: str,
    language: SupportedLanguage,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> TranslationResponse:
    return TranslationResponse(**await translation_service.generate(database, poi_id, language))


@router.put("/{language}", response_model=TranslationResponse)
async def update_translation(
    poi_id: str,
    language: SupportedLanguage,
    payload: TranslationUpdate,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> TranslationResponse:
    return TranslationResponse(
        **await translation_service.update(database, poi_id, language, payload.text)
    )


@router.post("/{language}/approve", response_model=TranslationResponse)
async def approve_translation(
    poi_id: str,
    language: SupportedLanguage,
    database: Any = Depends(get_database),
    _: dict[str, Any] = Depends(require_permission("content:write")),
) -> TranslationResponse:
    return TranslationResponse(**await translation_service.approve(database, poi_id, language))
