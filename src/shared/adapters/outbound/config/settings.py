from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables.

    See `.env.example` for the full list. Access via `get_settings()`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "back-deshka"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # API
    api_cors_origins: list[str] = Field(
        default_factory=lambda: ["deshka://", "http://localhost:8081"]
    )

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true"
    mongo_db_name: str = "numen"

    # Redis (for ARQ)
    redis_url: str = "redis://localhost:6379/0"

    # Auth / JWT
    jwt_secret: str = "change-me-in-production-this-is-not-secure-32chars"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    # Email verification
    verification_code_length: int = 6
    verification_code_ttl_minutes: int = 15
    verification_max_attempts: int = 5
    verification_resend_cooldown_seconds: int = 60

    # Free-plan capacity
    categories_free_limit: int = 2
    accounts_free_limit: int = 2
    credit_cards_free_limit: int = 1

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Storage (Cloudflare R2 — S3-compatible)
    r2_endpoint: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "deshka-receipts"

    # Sentry
    sentry_dsn: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
