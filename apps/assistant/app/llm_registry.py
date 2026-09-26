"""LLM model registry (T-201).

Свой код, паттерн адаптирован из lawcopilot/app/llm/registry.py.
ModelEntry dataclass + REGISTRY dict + helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ProviderKind = Literal["anthropic", "openai", "litellm"]


@dataclass(frozen=True)
class ModelEntry:
    """Описание LLM модели."""

    model_id: str
    provider_kind: ProviderKind
    description: str = ""
    context_window: int = 8192
    supports_streaming: bool = True
    litellm_params: dict = field(default_factory=dict)


# === Registry MVP (5 моделей, T-201) ===
REGISTRY: dict[str, ModelEntry] = {
    # Anthropic (нативный SDK)
    "anthropic/claude-sonnet-4-5": ModelEntry(
        model_id="claude-sonnet-4-5",
        provider_kind="anthropic",
        description="Anthropic Claude Sonnet 4.5 — default для Transit-AI",
        context_window=200_000,
    ),
    "anthropic/claude-3-5-haiku": ModelEntry(
        model_id="claude-3-5-haiku-20241022",
        provider_kind="anthropic",
        description="Anthropic Claude 3.5 Haiku — быстрая и дешёвая",
        context_window=200_000,
    ),
    # OpenAI (нативный SDK)
    "openai/gpt-4o-mini": ModelEntry(
        model_id="gpt-4o-mini",
        provider_kind="openai",
        description="OpenAI GPT-4o Mini — экономичный",
        context_window=128_000,
    ),
    "openai/gpt-4o": ModelEntry(
        model_id="gpt-4o",
        provider_kind="openai",
        description="OpenAI GPT-4o — высокая точность",
        context_window=128_000,
    ),
    # LiteLLM-proxy (OpenRouter, GigaChat, и др.)
    "litellm/deepseek-chat": ModelEntry(
        model_id="deepseek/deepseek-chat",
        provider_kind="litellm",
        description="DeepSeek через LiteLLM/OpenRouter",
        context_window=64_000,
    ),
}


def list_models() -> list[str]:
    """Sorted список всех model_id."""
    return sorted(REGISTRY.keys())


def resolve_profile(model_id: str) -> ModelEntry:
    """Получить ModelEntry или KeyError."""
    if model_id not in REGISTRY:
        raise KeyError(
            f"Unknown model: {model_id}. Available: {list_models()}"
        )
    return REGISTRY[model_id]
