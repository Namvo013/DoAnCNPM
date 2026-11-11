from pydantic import BaseModel

from app.schemas.poi import SupportedLanguage


class AudioResponse(BaseModel):
    poi_id: str
    language: SupportedLanguage
    audio_url: str
    voice: str | None
