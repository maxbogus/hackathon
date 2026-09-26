"""LLM adapter factory (T-201).

Создаёт правильный adapter по provider_kind из ModelEntry.
Паттерн адаптирован из lawcopilot/app/llm/registry.py:get_adapter().
"""

from __future__ import annotations

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.litellm_adapter import LiteLLMAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.config import settings
from app.llm_base import BaseLLMAdapter
from app.llm_registry import resolve_profile


def get_adapter(model_id: str | None = None) -> BaseLLMAdapter:
    """Создаёт adapter по model_id (default из settings)."""
    model_id = model_id or settings.default_model
    entry = resolve_profile(model_id)

    if entry.provider_kind == "anthropic":
        return AnthropicAdapter(
            model_id=entry.model_id,
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )
    if entry.provider_kind == "openai":
        return OpenAIAdapter(
            model_id=entry.model_id,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    if entry.provider_kind == "litellm":
        return LiteLLMAdapter(
            model_id=entry.model_id,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    raise ValueError(f"Unsupported provider_kind: {entry.provider_kind}")
