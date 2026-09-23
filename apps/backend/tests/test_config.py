"""Tests for app.config.Settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import REPO_ROOT, Settings


def test_settings_loads_with_defaults() -> None:
    """Default settings (no env vars) point to local dev URLs."""
    s = Settings(_env_file=None)  # ignore .env to test pure defaults
    assert s.app_env == "dev"
    assert s.app_version == "0.1.0"
    assert "postgresql+asyncpg" in s.database_url
    assert s.redis_url.startswith("redis://")


def test_settings_reads_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """TRANSIT_AI_* env vars override defaults."""
    monkeypatch.setenv("TRANSIT_AI_APP_ENV", "prod")
    monkeypatch.setenv("TRANSIT_AI_DEBUG", "true")
    monkeypatch.setenv(
        "TRANSIT_AI_DATABASE_URL", "postgresql+asyncpg://prod:prod@db:5432/prod"
    )

    s = Settings(_env_file=None)
    assert s.app_env == "prod"
    assert s.debug is True
    assert "prod" in s.database_url


def test_settings_cors_origins_default_for_dev() -> None:
    s = Settings(_env_file=None)
    assert "http://localhost:5173" in s.cors_origins


def test_settings_artifacts_dir_points_into_ml() -> None:
    s = Settings(_env_file=None)
    assert s.artifacts_dir == REPO_ROOT / "ml" / "artifacts"


def test_settings_app_env_must_be_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """app_env is a Literal, invalid values raise ValidationError."""
    monkeypatch.setenv("TRANSIT_AI_APP_ENV", "staging")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
