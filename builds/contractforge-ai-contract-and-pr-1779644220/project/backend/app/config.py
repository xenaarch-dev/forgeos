from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field("postgresql+asyncpg://app:app@localhost:5432/app")
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    app_secret: str = "change-me"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]

    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    lemonsqueezy_api_key: str = ""
    lemonsqueezy_webhook_secret: str = ""

    sentry_dsn_backend: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
