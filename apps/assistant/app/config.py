"""Assistant settings (T-201).

Environment variables для LLM провайдеров.
Читаются через pydantic-settings с префиксом TRANSIT_AI_.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Assistant settings."""

    model_config = SettingsConfigDict(
        env_prefix="TRANSIT_AI_LLM_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider selection
    default_model: str = "anthropic/claude-sonnet-4-5"
    default_provider: str = "anthropic"  # anthropic | openai | litellm

    # API keys (через env)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    gigachat_credentials: str | None = None

    # API endpoints
    anthropic_base_url: str = "https://api.anthropic.com"
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    gigachat_base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"

    # Limits
    request_timeout_sec: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
