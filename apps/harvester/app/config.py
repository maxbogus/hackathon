"""Harvester settings (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Strongly-typed harvester settings."""

    model_config = SettingsConfigDict(
        env_prefix="HARVESTER_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Modes
    mode: str = "local"  # local | online
    """local — читает из data/external/*.json (R4 hackathon-rules safe).
    online — ходит в Open-Meteo, OSM Overpass (только dev)."""

    # Paths
    data_dir: Path = REPO_ROOT / "data"
    external_dir: Path = REPO_ROOT / "data" / "external"

    # Online mode: API endpoints (опционально)
    openmeteo_url: str = "https://archive-api.open-meteo.com/v1/archive"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    http_timeout_sec: float = 30.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
