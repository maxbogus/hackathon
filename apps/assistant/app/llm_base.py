"""Base LLM adapter (T-201).

Абстрактный класс для всех LLM провайдеров. Паттерн адаптирован из
lawcopilot/app/llm/llm_base.py (BaseLLM abstract class), но это свой код.

Каждый провайдер (OpenAI, Anthropic, LiteLLM-proxy) реализует `generate()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMRequest:
    """Запрос к LLM."""

    prompt: str
    system_prompt: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.3
    model: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Ответ от LLM."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None  # оригинальный response object


class BaseLLMAdapter(ABC):
    """Базовый класс для LLM adapter."""

    def __init__(self, model_id: str, api_key: str | None = None, base_url: str | None = None):
        self.model_id = model_id
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Генерация ответа от LLM."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, request: LLMRequest):
        """Streaming генерация (async iterator)."""
        raise NotImplementedError
        yield  # type: ignore[unreachable]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_id})"
