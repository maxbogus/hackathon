"""Tests for LLM integration (T-201).

Тестируем:
- REGISTRY содержит MVP модели
- list_models() возвращает sorted
- resolve_profile() валидирует
- get_adapter() выбирает правильный adapter по provider_kind
"""

from __future__ import annotations

from app.llm_factory import get_adapter
from app.llm_registry import (
    REGISTRY,
    ModelEntry,
    list_models,
    resolve_profile,
)
import pytest

# === Registry tests ===

def test_registry_has_mvp_models() -> None:
    """В реестре есть MVP модели (минимум 5)."""
    assert len(REGISTRY) >= 5


def test_registry_has_anthropic_claude() -> None:
    """Default модель — Anthropic Claude Sonnet 4.5."""
    assert "anthropic/claude-sonnet-4-5" in REGISTRY


def test_registry_has_openai_gpt4o() -> None:
    """OpenAI GPT-4o в реестре."""
    assert "openai/gpt-4o-mini" in REGISTRY


def test_registry_has_litellm_deepseek() -> None:
    """DeepSeek через LiteLLM."""
    assert "litellm/deepseek-chat" in REGISTRY


def test_list_models_sorted() -> None:
    """list_models возвращает отсортированный список."""
    models = list_models()
    assert models == sorted(models)
    assert "anthropic/claude-sonnet-4-5" in models


def test_resolve_profile_known() -> None:
    """resolve_profile возвращает ModelEntry для известной модели."""
    entry = resolve_profile("anthropic/claude-sonnet-4-5")
    assert entry.provider_kind == "anthropic"
    assert entry.context_window == 200_000


def test_resolve_profile_unknown_raises() -> None:
    """resolve_profile KeyError на неизвестную модель."""
    with pytest.raises(KeyError) as exc_info:
        resolve_profile("nonexistent/model")
    assert "Unknown model" in str(exc_info.value)


# === get_adapter tests ===

def test_get_adapter_anthropic_creates_anthropic() -> None:
    """get_adapter("anthropic/...") создаёт AnthropicAdapter."""
    adapter = get_adapter("anthropic/claude-sonnet-4-5")
    from app.adapters.anthropic_adapter import AnthropicAdapter
    assert isinstance(adapter, AnthropicAdapter)
    assert "claude" in adapter.model_id


def test_get_adapter_openai_creates_openai(monkeypatch) -> None:
    """get_adapter("openai/...") создаёт OpenAIAdapter."""
    monkeypatch.setenv("TRANSIT_AI_LLM_OPENAI_API_KEY", "sk-test-fake-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")
    from app.config import get_settings
    get_settings.cache_clear()
    adapter = get_adapter("openai/gpt-4o-mini")
    from app.adapters.openai_adapter import OpenAIAdapter
    assert isinstance(adapter, OpenAIAdapter)


def test_get_adapter_litellm_creates_litellm() -> None:
    """get_adapter("litellm/...") создаёт LiteLLMAdapter."""
    adapter = get_adapter("litellm/deepseek-chat")
    from app.adapters.litellm_adapter import LiteLLMAdapter
    assert isinstance(adapter, LiteLLMAdapter)


def test_get_adapter_default_uses_settings() -> None:
    """Без аргумента использует settings.default_model."""
    adapter = get_adapter()
    assert adapter.model_id in ("claude-sonnet-4-5", "gpt-4o-mini", "deepseek/deepseek-chat")


# === Adapter base interface tests ===

def test_anthropic_adapter_implements_interface() -> None:
    """AnthropicAdapter реализует generate() и stream()."""
    from app.adapters.anthropic_adapter import AnthropicAdapter
    adapter = AnthropicAdapter(
        model_id="claude-sonnet-4-5", api_key=None, base_url=None
    )
    assert hasattr(adapter, "generate")
    assert hasattr(adapter, "stream")
    assert callable(adapter.generate)
    assert callable(adapter.stream)


def test_model_entry_dataclass() -> None:
    """ModelEntry — frozen dataclass."""
    entry = ModelEntry(
        model_id="test",
        provider_kind="openai",
        description="Test",
    )
    assert entry.model_id == "test"
    with pytest.raises(Exception):  # FrozenInstanceError
        entry.model_id = "other"  # type: ignore[misc]
