"""ML Pipeline settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """ML pipeline settings (Celery + DB + paths)."""

    model_config = SettingsConfigDict(
        env_prefix="ML_PIPELINE_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # DB (sync URL для SQLAlchemy sync engine в Celery tasks)
    database_url: str = (
        "postgresql+psycopg2://transit:transit@localhost:5432/transit_ai"
    )

    # Paths
    repo_root: Path = REPO_ROOT
    ml_artifacts_dir: Path = REPO_ROOT / "ml" / "artifacts"
    predictions_dir: Path = REPO_ROOT / "predictions"
    data_dir: Path = REPO_ROOT / "data"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
