---
id: T-115
phase: 7
title: README — добавить English version, исправить ссылки, отдельный раздел Handover
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 2.0
  C: 1.0
  score: 10.0
depends_on: []
blocks: []
tags: [docs, handover, beneficiary, hackathon]
status: ready
created: 2026-09-23
updated: 2026-09-23
scope: "Russian README only — English not required (see T-141 for UI text registry)"
assignee: "maxim"
---

# T-115: README — добавить English version, исправить ссылки, отдельный раздел Handover

## Context

Лучшие проекты хакатона, по словам организаторов, «могут быть рекомендованы к внедрению
в инфраструктуру московского транспорта». Для этого нужна документация, которую Департамент
транспорта может прочитать без контекста разработки.

**Принятое решение:** хакатон русский → README на русском (для Департамента), UI на русском, код и комментарии на английском. English version README НЕ нужна.

**Миграция UI-текстов:** см. отдельный тикет T-141 (apps/frontend/src/lib/i18n/) — text registry с типизированным `t(key)`. T-115 не занимается аудитом хардкода на фронте.

**Прогресс:** базовая русская версия README.md уже написана (12 разделов, бенефициары,
метрики успеха, Quick Start, Makefile-команды, технологии). Осталось:

- Исправить ссылки на несуществующие файлы (`docs/ARCHITECTURE.md`, `docs/HACKATHON_RULES.md`,
  `docs/DATA_CONTRACTS.md`, `docs/USER_STORIES.md`, `docs/ML.md`, `docs/HACKATHON_CHECKLIST.md`,
  `docs/PROMPTS/`, `docs/ledger/README.md` — проверить какие реально существуют).
- Добавить English version (для open-source).
- Выделить отдельный раздел Handover в Департамент (контакты, лицензия, что нужно для внедрения).
- Добавить раздел «Где смотреть метрики модели» — ссылка на `docs/reports/` и текущую активную модель.

## Acceptance Criteria

- [x] Обновлён корневой `README.md` (есть 12 разделов)
- [x] Раздел «Бенефициары»: Департамент, диспетчеры, пассажиры — описаны явно
- [x] Раздел «Метрики успеха для города» — таблица с baseline → наше решение → улучшение
- [x] Раздел «Быстрый старт» — `make install && make seed && make train && yarn dev`
- [x] Раздел «Архитектура» — ссылка на `docs/architecture/` (schema.dbml есть) и краткое описание
- [x] Раздел «Контракты» — OpenAPI URL, JSON Schema для predictions (через docs/api/openapi.json)
- [ ] Раздел «Handover в Департамент» — что нужно для внедрения, контакты, лицензия (выделить отдельно)
- [x] Раздел «Данные» — какие источники используются, ограничения (через ссылку на requirements.md)
- [ ] Раздел «Где метрики модели» — ссылка на `docs/reports/`, текущая активная модель
- [x] README на русском (для Департамента) — есть
- [x] README.en.md — НЕ НУЖЕН (хакатон русский, код и комментарии на английском, UI на русском)

## Technical Notes

**Что проверить и исправить:**

```bash
# Какие файлы из README реально существуют?
ls docs/ARCHITECTURE.md docs/HACKATHON_RULES.md docs/DATA_CONTRACTS.md \
   docs/USER_STORIES.md docs/ML.md docs/HACKATHON_CHECKLIST.md \
   docs/PROMPTS/ docs/ledger/README.md 2>&1
# Удалить из README битые ссылки, добавить актуальные.
```

**Актуальные ссылки в проекте:**
- `AGENTS.md` — ✅
- `.clinerules/00-AGENTS.md` — ✅
- `docs/hackathon/requirements.md` — ✅
- `docs/hackathon/presentation/slide_01_pain_points.md` — ✅
- `docs/api/openapi.json` — ✅ (генерируется backend)
- `docs/architecture/schema.dbml` — ✅
- `docs/architecture/schema-tables.md` — ✅
- `docs/ledger/decisions.jsonl` — ✅
- `docs/backlog/STATUS.md` — ✅
- `ml/transit_ai/...` — ✅

**Что нужно сделать:**
1. Аудит ссылок: убрать неработающие (`docs/ARCHITECTURE.md`, `docs/HACKATHON_RULES.md`,
   `docs/DATA_CONTRACTS.md`, `docs/USER_STORIES.md`, `docs/ML.md`,
   `docs/HACKATHON_CHECKLIST.md`, `docs/PROMPTS/`, `docs/ledger/README.md`).
2. Добавить раздел «Handover в Департамент» с подразделами:
   - Что готово к внедрению (артефакты, API, документация)
   - Что нужно от Департамента (реальные данные, доступ к API)
   - Контакты команды
   - Лицензия (текущая MIT, обсуждается)
3. Добавить раздел «Метрики модели» с динамической ссылкой на активную модель
   (`ml/artifacts/active.json` → model_id → docs/reports/<model>_metrics.json).

## Verification

```bash
# Все ссылки из README ведут на существующие файлы
grep -oE "\[[^]]+\]\(([^)]+\.md|[^)]+/)\)" /home/maxbogus/Repositories/hackathon/README.md | \
  grep -oE "\([^)]+\)" | tr -d '()' | while read f; do
    [ -e "/home/maxbogus/Repositories/hackathon/${f#./}" ] || echo "BROKEN: $f"
  done
# Должно вернуть 0 строк

# Раздел Handover присутствует
grep -E "^## .*[Hh]andover" README.md
```

## Beneficiary Impact

**Департамент транспорта (⭐⭐⭐⭐⭐)** — handover = готовность к внедрению = рекомендация жюри.
**Open-source сообщество** — MIT + English README = реиспользование.

RICE: 10.0 — **топ-7 приоритет**. Дешёвая задача с высоким импактом для жюри.
