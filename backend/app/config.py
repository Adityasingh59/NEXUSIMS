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

    # Database (nexus_app for app; nexus_admin for migrations)
    DATABASE_URL: str = "postgresql+asyncpg://nexus_app:nexus_dev_password@localhost:5432/nexus_ims"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/1"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_TTL_MINUTES: int = 15
    JWT_REFRESH_TOKEN_TTL_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    def get_async_database_url(self) -> str:
        """Convert DATABASE_URL to async protocol if needed (for Railway compatibility)."""
        url = self.DATABASE_URL
        # Railway provides postgresql:// but we need postgresql+asyncpg://
        if url and "postgresql://" in url and "postgresql+asyncpg://" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
