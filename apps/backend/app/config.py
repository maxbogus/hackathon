"""Application settings (pydantic-settings).

Reads from environment + `.env` file. All env vars are uppercased with
prefix `TRANSIT_AI_` (or unset → defaults for local dev).

Usage:
    from app.config import settings
    settings.database_url   # postgresql+asyncpg://...
    settings.app_env        # "dev" | "prod"
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = apps/backend/app/config.py → 3 levels up
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="TRANSIT_AI_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: Literal["dev", "test", "prod"] = "dev"
    app_version: str = "0.1.0"
    debug: bool = False

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://transit:transit@localhost:5432/transit_ai",
        description="SQLAlchemy async URL.",
    )

    # --- Redis ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching.",
    )
    redis_cache_ttl_seconds: int = Field(default=60, ge=0)

    # --- CORS ---
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins (frontend dev servers).",
    )

    # --- ML artifacts ---
    artifacts_dir: Path = Field(default=REPO_ROOT / "ml" / "artifacts")
    artifacts_schema_path: Path = Field(
        default=REPO_ROOT / "docs" / "schemas" / "prediction_artifact.schema.json"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton (rebuild only if env changes between tests)."""
    return Settings()


# Convenience singleton — most callers will use this
settings = get_settings()


__all__ = ["REPO_ROOT", "Settings", "get_settings", "settings"]
