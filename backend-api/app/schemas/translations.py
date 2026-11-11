from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.schemas.poi import SupportedLanguage

TARGET_LANGUAGES = (
    SupportedLanguage.EN,
    SupportedLanguage.JA,
    SupportedLanguage.KO,
    SupportedLanguage.ZH,
)


class TranslationStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class TranslationUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class TranslationPreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    target_languages: list[SupportedLanguage] = Field(
        default_factory=lambda: list(TARGET_LANGUAGES),
        min_length=1,
        max_length=len(TARGET_LANGUAGES),
    )

    @field_validator("target_languages")
    @classmethod
    def validate_target_languages(
        cls,
        value: list[SupportedLanguage],
    ) -> list[SupportedLanguage]:
        if SupportedLanguage.VI in value or len(set(value)) != len(value):
            raise ValueError("Translation targets must be unique non-Vietnamese languages")
        return value


class TranslationResponse(BaseModel):
    poi_id: str
    language: SupportedLanguage
    text: str
    status: TranslationStatus
    created_at: str
    updated_at: str
    published_at: str | None
