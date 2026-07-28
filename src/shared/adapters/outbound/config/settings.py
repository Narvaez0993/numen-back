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
    # Watched categories. The global cap is not here: every user has exactly one.
    budget_categories_free_limit: int = 2
    # Open pockets at once; archived goals never count.
    goals_active_free_limit: int = 1

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Assistant — model + pricing (USD per MTok; revisit when intro pricing ends)
    anthropic_model: str = "claude-sonnet-5"
    anthropic_max_tokens: int = 4096
    anthropic_effort: str = "low"
    anthropic_input_usd_per_mtok: float = 3.0
    anthropic_output_usd_per_mtok: float = 15.0
    # Assistant — the two flat counters (docs 02 §10) and the chat loop bounds
    assistant_registrations_free_limit: int = 60
    assistant_registrations_plus_limit: int = 300
    assistant_messages_free_limit: int = 10
    assistant_messages_plus_limit: int = 300
    # Messages served past the limit before the hard gate (the nudge window).
    assistant_message_grace: int = 3
    assistant_history_window: int = 24
    assistant_max_tool_iterations: int = 6

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
