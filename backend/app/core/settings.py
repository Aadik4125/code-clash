from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".." / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CogniVara API"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cognivara"
    alembic_database_url: str | None = None

    jwt_secret_key: str = "replace-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 60 * 24

    audio_storage_provider: str = "local"
    local_upload_dir: str = str(BASE_DIR / "uploads")
    aws_s3_bucket: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    hf_api_key: str | None = None
    hf_stt_model: str = "openai/whisper-large-v3-turbo"
    transcription_provider: str = "huggingface"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    sentry_dsn: str | None = None
    fast_analysis_mode: bool = False

    @property
    def effective_alembic_url(self) -> str:
        return self.alembic_database_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

