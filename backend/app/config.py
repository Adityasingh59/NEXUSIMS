"""NEXUS IMS — Application configuration via pydantic-settings."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_TTL_MINUTES: int = 15
    JWT_REFRESH_TOKEN_TTL_DAYS: int = 7

    # ✅ CORS (FIXED FOR PYDANTIC V2)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ✅ Allow ALL Vercel preview deployments
    CORS_ALLOW_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"


@lru_cache
def get_settings() -> Settings:
    return Settings()
