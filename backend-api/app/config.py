from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Multilingual Tourist Guide API"
    environment: str = "development"
    demo_mode: bool = False
    api_prefix: str = "/api"
    database_url: str = (
        "mssql+aioodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D"
        "%3BSERVER%3Dlocalhost%5CSQLEXPRESS%3BDATABASE%3DCNPM"
        "%3BTrusted_Connection%3Dyes%3BTrustServerCertificate%3Dyes"
    )
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    admin_seed_email: str = "admin@example.com"
    admin_seed_password: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    upload_dir: str = "uploads"
    public_base_url: str = "http://localhost:8000"
    public_app_url: str = "http://localhost:5500"
    heatmap_grid_size_meters: int = 250
    auth_service_url: str = "http://localhost:8101"
    poi_service_url: str = "http://localhost:8102"
    presence_service_url: str = "http://localhost:8103"
    internal_service_token: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def reject_example_secret(cls, value: str) -> str:
        if value == "replace-with-a-long-random-secret":
            raise ValueError("Replace the example JWT secret before starting the API")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
