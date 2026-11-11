from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.poi import SupportedLanguage


class VisitorHeartbeat(BaseModel):
    type: Literal["heartbeat"]
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    poi_id: str | None = None
    language: SupportedLanguage | None = None

    @model_validator(mode="after")
    def require_coordinate_pair(self) -> "VisitorHeartbeat":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        return self
