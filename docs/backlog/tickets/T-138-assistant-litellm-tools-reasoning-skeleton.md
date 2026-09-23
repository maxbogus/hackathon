---
id: T-138
phase: 5
title: apps/assistant — LiteLLM провайдер + tools registry + Reasoning (lawcopilot-паттерн, MVP)
priority: P2
effort: 6
unit: hours
rice:
  R: 5
  I: 2.0
  C: 0.9
  score: 1.5
depends_on: []
blocks: [T-139]
tags: [assistant, llm, litellm, tools, reasoning, lawcopilot, hackathon, differentiator]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-138: apps/assistant — LiteLLM провайдер + tools + Reasoning (lawcopilot-паттерн, MVP)

## Context

AGENTS.md и clinerule 11 заявляют LLM-ассистента как **дифференциатор**. D-002 зафиксировал
lawcopilot-паттерн (LiteLLM + Reasoning + tools).

**Текущее состояние (КРИТИЧНО):**
- apps/assistant/app/ — все подпапки пустые (adapters/, providers/, tools/, prompts/).
- Ни одного файла кода ассистента нет.
- Без ассистента MCP (T-139) тоже невозможен.

Этот тикет реализует **минимум**: один провайдер (OpenRouter через LiteLLM), 3 базовых
tools, system prompt, ReasoningConfig.

## Acceptance Criteria

- [ ] Зависимости: litellm>=1.40, anthropic>=0.30, httpx>=0.27
- [ ] apps/assistant/pyproject.toml обновлён
- [ ] apps/assistant/app/providers/registry.py — registry моделей
- [ ] apps/assistant/app/providers/litellm_adapter.py — обёртка LiteLLM
- [ ] apps/assistant/app/reasoning.py — ReasoningConfig (effort: NONE..XHIGH)
- [ ] apps/assistant/app/tools/__init__.py — TOOLS dict
- [ ] 3 tool'а: get_predictions_for_route, get_overload_alerts, list_models
- [ ] Каждый tool — async, типизированный input/output + JSON Schema для MCP
- [ ] apps/assistant/app/prompts/transit_system.md — system prompt
- [ ] apps/assistant/app/harness.py — Harness с tool-calling loop (max_tool_rounds=20)
- [ ] apps/assistant/scripts/test_chat.py — smoke test
- [ ] Минимум 3 unit-теста: test_reasoning.py, test_providers.py, test_harness.py
- [ ] Документация: apps/assistant/README.md

## Technical Notes

Структура:
```
apps/assistant/app/
├── __init__.py
├── providers/registry.py, litellm_adapter.py
├── reasoning.py
├── tools/__init__.py, predictions.py, alerts.py, models.py
├── prompts/transit_system.md
└── harness.py
```

Provider registry (минимум):
```python
REGISTRY = {
    "openrouter/deepseek/deepseek-chat": ModelEntry(
        provider_kind="litellm",
        litellm_params={"temperature": 0.3, "max_tokens": 2000},
    ),
    "openai/gpt-4o-mini": ModelEntry(
        provider_kind="litellm",
        litellm_params={"temperature": 0.5},
    ),
}
```

Tool schema (для MCP, из clinerule 12):
```python
async def get_predictions_for_route(
    route_id: int,
    horizon: Literal["day", "month", "year"] = "day",
) -> dict:
    """Получить прогноз пассажиропотока для маршрута."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{settings.backend_url}/api/v1/predictions/route/{route_id}",
            params={"horizon": horizon},
        )
        r.raise_for_status()
        return r.json()
```

Установка:
```bash
cd apps/assistant && uv add litellm anthropic httpx pydantic
uv add --dev pytest pytest-asyncio respx
```

## Verification

```bash
# 1. Зависимости
cd apps/assistant && uv sync

# 2. Type-check
cd apps/assistant && uv run mypy app/

# 3. Unit-тесты
cd apps/assistant && uv run pytest tests/ -v

# 4. Smoke chat
cd apps/assistant && OPENROUTER_API_KEY=$KEY uv run python scripts/test_chat.py
# Ожидаем: tool get_predictions_for_route вызван
```

## Beneficiary Impact

**Жюри (⭐⭐⭐⭐⭐)** — LLM-ассистент = killer-feature.
**Диспетчер (⭐⭐⭐⭐)** — natural language interface.
**Департамент (⭐⭐⭐)** — MCP (T-139) для Claude Desktop.

RICE: 1.5 — формально низкий, но большой импакт на впечатление жюри.
