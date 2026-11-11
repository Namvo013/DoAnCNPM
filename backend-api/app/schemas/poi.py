from typing import Annotated

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPORTED_LANGUAGES = frozenset({"vi", "en", "ja", "ko", "zh"})


class SupportedLanguage(str, Enum):
    VI = "vi"
    EN = "en"
    JA = "ja"
    KO = "ko"
    ZH = "zh"


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


PoiName = Annotated[str, Field(min_length=1, max_length=200)]
PoiCategory = Annotated[str, Field(min_length=1, max_length=100)]
PoiContent = dict[str, Annotated[str, Field(min_length=1, max_length=50_000)]]
PoiTranslations = dict[str, Annotated[str, Field(min_length=1, max_length=200)]]


def reject_unsupported_languages(value: dict[str, str]) -> dict[str, str]:
    unsupported = set(value) - SUPPORTED_LANGUAGES
    if unsupported:
        raise ValueError(f"Unsupported languages: {', '.join(sorted(unsupported))}")
    return value


class PoiCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PoiName
    coordinates: Coordinates
    geofence_radius_m: int = Field(ge=10, le=1000)
    image_url: str | None = Field(default=None, max_length=2048)
    category: PoiCategory
    content: PoiContent
    is_active: bool = True
    name_translations: PoiTranslations = Field(default_factory=dict)
    category_translations: PoiTranslations = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def validate_supported_languages(cls, value: PoiContent) -> PoiContent:
        unsupported = set(value) - SUPPORTED_LANGUAGES
        if unsupported:
            raise ValueError(f"Unsupported languages: {', '.join(sorted(unsupported))}")
        return value

    @field_validator("name_translations", "category_translations")
    @classmethod
    def validate_translation_languages(cls, value: PoiTranslations) -> PoiTranslations:
        return reject_unsupported_languages(value)

    @model_validator(mode="after")
    def require_vietnamese(self) -> "PoiCreate":
        if not self.content.get("vi", "").strip():
            raise ValueError("Vietnamese content is required")
        return self


class PoiUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PoiName | None = None
    coordinates: Coordinates | None = None
    geofence_radius_m: int | None = Field(default=None, ge=10, le=1000)
    image_url: str | None = Field(default=None, max_length=2048)
    category: PoiCategory | None = None
    content: PoiContent | None = None
    is_active: bool | None = None
    name_translations: PoiTranslations | None = None
    category_translations: PoiTranslations | None = None

    @field_validator("content")
    @classmethod
    def validate_content_languages(cls, value: PoiContent | None) -> PoiContent | None:
        if value is None:
            return None
        unsupported = set(value) - SUPPORTED_LANGUAGES
        if unsupported:
            raise ValueError(f"Unsupported languages: {', '.join(sorted(unsupported))}")
        if not value.get("vi", "").strip():
            raise ValueError("Vietnamese content is required")
        return value

    @field_validator("name_translations", "category_translations")
    @classmethod
    def validate_translation_languages(cls, value: PoiTranslations | None) -> PoiTranslations | None:
        if value is None:
            return None
        return reject_unsupported_languages(value)


class PoiResponse(BaseModel):
    id: str
    name: str
    coordinates: Coordinates
    geofence_radius_m: int
    image_url: str | None
    category: str
    content: PoiContent
    content_language: str | None = None
    name_translations: dict[str, str] = Field(default_factory=dict)
    category_translations: dict[str, str] = Field(default_factory=dict)
    audio: dict[str, str] = Field(default_factory=dict)
    is_active: bool


class PoiListResponse(BaseModel):
    items: list[PoiResponse]
    total: int
