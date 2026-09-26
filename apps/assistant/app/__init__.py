"""Transit-AI Assistant (T-201) — LLM endpoint.

Интеграция с LLM провайдерами через LiteLLM + Anthropic SDK.
Паттерн (ModelEntry dataclass, REGISTRY dict, BaseAdapter abstract class)
адаптирован из lawcopilot/app/llm/registry.py — но это свой код,
адаптированный под Transit-AI специфику.

Поддерживаемые провайдеры:
  - OpenAI (gpt-4o-mini)
  - Anthropic (claude-sonnet-4-5)
  - OpenRouter (deepseek, gigachat, и др.)
  - GigaChat (SberDevices)
  - LiteLLM proxy для других

Usage:
    from app.llm import get_adapter, REGISTRY
    adapter = get_adapter("anthropic/claude-sonnet-4-5")
    response = await adapter.generate("Explain tram schedule")
"""

from app.llm_base import BaseLLMAdapter, LLMRequest, LLMResponse
from app.llm_factory import get_adapter
from app.llm_registry import REGISTRY, ModelEntry, list_models, resolve_profile

__all__ = [
    "REGISTRY",
    "BaseLLMAdapter",
    "LLMRequest",
    "LLMResponse",
    "ModelEntry",
    "get_adapter",
    "list_models",
    "resolve_profile",
]
