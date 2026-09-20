# 11-assistant-pattern.md — LLM ассистент (lawcopilot-паттерн)

## Что это

LLM-ассистент для диспетчера: задаёшь вопрос на естественном языке —
получаешь ответ + визуализацию (карта с подсветкой, график прогноза).

## Архитектура (из lawcopilot)

```
User (фронт) → /api/v1/chat (FastAPI) → assistant (apps/assistant/)
                                              ├─ providers/ (LiteLLM, Anthropic, OpenRouter)
                                              ├─ reasoning.py (ReasoningConfig)
                                              ├─ harness.py (цикл хода с tool-calling)
                                              ├─ prompts/ (system prompts)
                                              └─ tools/ (tools ассистента)
                                                    ├─ predictions.py → API /predictions
                                                    ├─ insights.py → API + вычисления
                                                    ├─ scenarios.py → Monte Carlo
                                                    ├─ models.py → registry API
                                                    └─ validation.py → inventory report
```

## Провайдеры

LiteLLM-адаптер (из `lawcopilot/app/llm/adapters/litellm_adapter.py`).
Поддерживает OpenRouter, OpenAI, Anthropic, DeepSeek, GigaChat.

Регистрация (из `lawcopilot/app/llm/registry.py`):

```python
# apps/assistant/app/providers/registry.py
REGISTRY: dict[str, ModelEntry] = {
    "openai/gpt-4o-mini": ModelEntry(
        provider_kind="litellm",
        api_base=None,  # default
        litellm_params={"temperature": 0.3},
    ),
    "anthropic/claude-3-5-sonnet": ModelEntry(
        provider_kind="anthropic",  # нативный SDK для citations
    ),
    "deepseek/deepseek-v4-flash": ModelEntry(
        provider_kind="litellm",
        litellm_params={"temperature": 0.7, "max_tokens": 8000},
    ),
    "gigachat/GigaChat-Pro": ModelEntry(
        provider_kind="litellm",
        api_base="https://gigachat.devices.sberbank.ru/api/v1",
        litellm_params={"temperature": 0.5},
    ),
}
```

## Capability profiles

Каждая модель имеет capability-профиль (из `lawcopilot/app/llm/canonical/capability.py`):

```python
_PROFILES = {
    "openai/gpt-4o-mini": {
        "L1": {"tool_calling": True, "streaming": True, "system_prompt": True},
        "L2": {"reasoning_in_response": False, "cache_tokens_in_usage": True},
    },
    "anthropic/claude-3-5-sonnet": {
        "L1": {"tool_calling": True, "streaming": True, "parallel_tool_calls": False},
        "L2": {"reasoning_in_response": True, "structured_json_schema": True},
    },
    "deepseek/deepseek-v4-flash": {
        "L1": {"tool_calling": True, "streaming": True},
        "L2": {"reasoning_in_response": True, "reasoning_in_history": True},
    },
}
```

## Reasoning

Из `lawcopilot/app/llm/llm_reasoning.py`:

```python
# apps/assistant/app/reasoning.py
class ReasoningEffort(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"   # ~10% токенов
    LOW = "low"           # ~20%
    MEDIUM = "medium"     # ~50% (default)
    HIGH = "high"         # ~80%
    XHIGH = "xhigh"       # ~95%

@dataclass
class ReasoningConfig:
    enabled: bool = True
    effort: ReasoningEffort | None = None
    max_tokens: int | None = None  # для Anthropic-style

    @classmethod
    def for_complex_query(cls, budget: int = 16000):
        return cls(enabled=True, max_tokens=budget)
```

Бюджеты из env:
- `LLM_REASONING_BUDGET_SIMPLE=2000`
- `LLM_REASONING_BUDGET_MODERATE=8000`
- `LLM_REASONING_BUDGET_COMPLEX=16000`

## Harness (цикл хода)

Из `lawcopilot/app/chat/harness.py`:

```python
# apps/assistant/app/harness.py
class Harness:
    """Один ход беседы: запросы к модели до end_turn, инструменты между ними."""

    def __init__(
        self,
        client: BaseProvider,
        tools: dict[str, ToolHandler],
        ledger: SpendLedger,
        max_tool_rounds: int = 20,
        max_continuations: int = 5,
    ):
        ...

    async def run(
        self,
        build: RequestBuilder,
        messages: list[dict],
        is_cancelled: Callable | None = None,
    ) -> AsyncIterator[Event]:
        """Стримит события: block_start/delta/stop, tool_result, message, usage, done."""
```

События:
- `block_start`, `block_delta`, `block_stop` — стрим SDK
- `tool_result` — наш инструмент выполнен
- `assistant_message`, `user_message` — для transcript
- `usage`, `status`, `error`, `done`

## Tools

Каждый tool — Python async функция с типизированным input/output.

```python
# apps/assistant/app/tools/predictions.py
async def get_predictions_for_route(
    route_id: int,
    from_date: str | None = None,
    to_date: str | None = None,
    horizon: Literal["day", "month", "year"] = "day",
) -> dict:
    """Получить прогноз пассажиропотока для маршрута.
    Возвращает: {data: [{period_start, value, lower, upper}], metadata: {...}}.
    """
    # Вызывает наш backend через httpx
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BACKEND_URL}/api/v1/predictions/route/{route_id}",
            params={"from": from_date, "to": to_date, "horizon": horizon},
        )
        r.raise_for_status()
        return r.json()
```

Регистрация в `apps/assistant/app/tools/__init__.py`:

```python
TOOLS = {
    "get_predictions_for_route": get_predictions_for_route,
    "get_top_congested_stops": get_top_congested_stops,
    "run_simulation": run_simulation,            # Monte Carlo
    "list_models": list_models,
    "activate_model": activate_model,
    "get_validation_report": get_validation_report,
}
```

## System prompt

`apps/assistant/prompts/system_transit.md`:

```markdown
Ты AI-ассистент диспетчера трамвайной сети Москвы.

Твоя задача — помогать с вопросами о пассажиропотоке:
- Показывать прогнозы по остановкам, маршрутам, районам
- Находить перегруженные остановки в заданное время
- Сравнивать прогноз с фактом за прошлые периоды
- Запускать сценарии "что если" (Monte Carlo)

Доменные определения:
- "Утренний пик" = 7:00–10:00 (будни)
- "Вечерний пик" = 17:00–20:00 (будни)
- "Центр" = ЦАО (районы Арбат, Тверской, Хамовники, ...)
- "Спальники" = районы за МКАД с преобладанием жилой застройки

Всегда указывай источник данных (какая модель, какой период).
При перегруженных остановках предлагай конкретные действия.
```

## MCP интеграция

`apps/mcp/server.py` повторяет tools ассистента, но в JSON-RPC формате.
Дублирование намеренное: MCP не зависит от FastAPI assistant, может работать
в standalone режиме (stdio).

См. `.clinerules/12-mcp-draft.md`.

## Тестирование

```bash
# Smoke test registry
make assistant-test

# Reasoning test (DeepSeek R1)
make assistant-reasoning

# Chat smoke
cd apps/assistant && uv run python scripts/test_chat.py
```

## Что НЕ делаем

- ❌ Использовать LLM > 4B для inference (R2 в hackathon-rules)
- ❌ Дублировать бизнес-логику (tools тонкие — вызывают API)
- ❌ Хранить историю чатов (для хакатона не нужно)
- ❌ Использовать agent loop без лимита (max_tool_rounds=20 обязательно)
