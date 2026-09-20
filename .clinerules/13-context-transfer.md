# 13-context-transfer.md — Трансфер контекста между сессиями

## Правило (ОБЯЗАТЕЛЬНОЕ)

Каждый ответ агента по этому проекту должен заканчиваться блоком
`## CONTEXT HANDOFF` ЛИБО обновлять `docs/HANDOFF.md` (источник истины).

Это нужно, чтобы переносить контекст в новую сессию при переполнении
контекстного окна LLM (~170K токенов рабочий бюджет, см. `MEMORY-BUDGET.md`).

## Формат блока (6 строк, строго)

```
## CONTEXT HANDOFF
- Цель: <одна строка — к чему идём>
- Состояние: <LB / последний коммит / что уже сделано>
- Последнее решение: <что приняли и почему>
- Следующая задача: <T-NNN + команда запуска>
- Артефакты на диске: <файлы/кэши, откуда продолжить>
- Открытые вопросы: <что не решено>
```

## Правила

1. Handoff пишется ПОСЛЕ каждого ответа, даже короткого.
2. «Следующая задача» — всегда ОДНА атомарная проверка (T-NNN), не список.
3. Если `docs/HANDOFF.md` существует — он источник истины, не история чата.
4. Перед стартом новой сессии: прочитать `docs/HANDOFF.md` + `docs/backlog/STATUS.md`.
5. В конце сессии ВСЕГДА обновлять `docs/HANDOFF.md` через `make handoff-update`.
6. Если в ответе есть важное решение — добавить в ledger через `make ledger-add`.

## Расположение HANDOFF.md

`docs/HANDOFF.md` — один файл, перезаписывается при каждом обновлении.
Формат:

```markdown
# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-20 15:30 UTC
> Обновлено: Cline (агент) после T-042

## Цель

Доделать MVP (baseline + XGBoost + frontend карта) до хакатона.

## Что сделано

- T-001..T-013: toolchain и clinerules
- T-014..T-022: backend skeleton
- T-023..T-031: ML pipeline + baseline + XGBoost
- T-032..T-047: contracts + backend loader + endpoints
- T-048..T-061: frontend (каркас + Orval + MapProvider + Dashboard)

## Что в работе

- T-062..T-074: LLM ассистент + MCP черновик

## Следующая задача

**T-062:** apps/assistant/pyproject.toml (litellm, anthropic, aiohttp)

Команда запуска:
```bash
make assistant-test
```

## Открытые вопросы

- Какой провайдер выбрать для демо? OpenRouter или DeepSeek R1?
- Нужен ли HTTP+SSE MCP или хватит stdio?
- Нужна ли калибровка для XGBoost (пока без неё)?

## Артефакты на диске

- ml/artifacts/baseline_v1/ — рабочая baseline модель
- ml/artifacts/xgboost_v1/ — XGBoost с RMSLE 0.42 на синтетике
- predictions/2026-09-20.parquet — последний прогноз
- docs/api/openapi.json — свежий
- apps/frontend/src/generated/ — синхронизирован с OpenAPI

## Последние 3 решения в ledger

- D-001: ML вне Docker (обоснование в docs/ledger/decisions.jsonl)
- D-002: Использовать lawcopilot-паттерн для assistant
- D-003: MapProvider strategy для переключения OSM ↔ Yandex

## Не делать в следующей сессии

- ❌ Не трогать скелет (он стабилен)
- ❌ Не менять контракт OpenAPI без обновления всех downstream
- ❌ Не патчить generated/ файлы
```

## Когда обновлять

| Событие | Действие |
|---|---|
| Закончен тикет | Обновить "Что сделано", "Что в работе" |
| Принято ADR | Обновить "Последние решения в ledger" |
| Изменился контракт | Обновить "Артефакты на диске" |
| Появились новые вопросы | Обновить "Открытые вопросы" |
| Сессия заканчивается | `make handoff-update` |

## Чего избегать

- ❌ Не копировать handoff в ответ (это дублирование и трата токенов)
- ❌ Не писать длинные блоки (6 строк строго)
- ❌ Не упоминать внутренние переписки (только суть)
- ❌ Не забывать про ledger (решения и находки отдельно)

## Пример правильного handoff

```
## CONTEXT HANDOFF
- Цель: завершить T-042 (predictions endpoint) с кэшированием в Redis
- Состояние: tests проходят (5/5), endpoint работает, commit f8a3b21
- Последнее решение: кэш на 60 сек (через Redis), ключ stop_id+from+to+horizon
- Следующая задача: T-042 → добавить api-check в pre-commit hook
- Артефакты на диске: apps/backend/app/api/predictions.py, tests/test_predictions.py
- Открытые вопросы: нужен ли rate limiting (RICE 4.5 — отложить)
```

## Anti-pattern

```
❌ Плохой handoff (слишком много):
## CONTEXT HANDOFF
- Цель: ...
- Состояние: ... (50 строк деталей)
- Последнее решение: ...
- Следующая задача: T-042, T-043, T-044, T-045, T-046 (список)
- ...
```

```
✅ Хороший handoff (6 строк, одна следующая задача):
## CONTEXT HANDOFF
- Цель: T-042 с Redis-кэшем
- Состояние: 5/5 tests passed, f8a3b21
- Последнее решение: cache 60s по stop_id+from+to+horizon
- Следующая задача: T-042 → api-check в pre-commit
- Артефакты: apps/backend/app/api/predictions.py
- Открытые: rate limiting (RICE 4.5)
```
