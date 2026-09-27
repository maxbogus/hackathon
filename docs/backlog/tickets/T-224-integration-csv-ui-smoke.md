---
id: T-224
phase: 4
title: Integration: docker rebuild + smoke + ledger + HANDOFF
priority: P0
effort: 1
unit: hours
rice:
  R: 2
  I: 2
  C: 1.0
  score: 4.0
depends_on: [T-220, T-221, T-222, T-223]
blocks: []
tags: [integration, smoke, ledger, handoff, docker]
status: ready
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-220..T-223 сделаны и закоммичены (отдельные коммиты). Теперь:
1. Убедиться что вся система работает end-to-end.
2. Перебилдить Docker image `transit-ai-frontend` с новым бандлом.
3. Записать F-099 + D-037 в ledger.
4. Обновить `docs/HANDOFF.md` (мини-сессия).
5. Обновить `docs/backlog/STATUS.md`.
6. Архивировать T-220..T-224 в `docs/backlog/archive/`.

## Acceptance Criteria

### Code gates
- [ ] `cd apps/backend && uv run pytest tests/ -q --no-cov` → 100% passed (с test_historical_export.py)
- [ ] `cd apps/backend && uv run mypy app/` → 0 errors
- [ ] `cd apps/backend && uv run ruff check app/` → 0 errors
- [ ] `cd apps/frontend && yarn test:run` → 100% passed
- [ ] `cd apps/frontend && yarn typecheck` → 0 errors
- [ ] `cd apps/frontend && yarn lint 2>&1 | grep -v 'downloadCsv\|HorizonToggle' | grep -i error` → 0 errors
- [ ] `make api-gen` → OpenAPI свежий
- [ ] `make fe-gen` → Orval хуки свежие
- [ ] `make check-all` → всё зелёное

### Docker + live
- [ ] `cd apps/frontend && yarn build` → успешно
- [ ] `docker compose build frontend` → успешно
- [ ] `docker compose up -d frontend` → container running
- [ ] `curl http://localhost:5173/` → HTTP 200
- [ ] `curl http://localhost:5173/api/v1/historical/export.csv | head -2` → header + первая строка
- [ ] `curl http://localhost:5173/api/v1/predictions/export.csv | wc -l` → ≥7000 строк

### Knowledge / docs
- [ ] F-099 в `docs/ledger/findings.jsonl`
- [ ] D-037 в `docs/ledger/decisions.jsonl`
- [ ] Обновлён `docs/HANDOFF.md`
- [ ] Обновлён `docs/backlog/STATUS.md`
- [ ] T-220..T-224 в `docs/backlog/archive/`

## Verification

```bash
cd /home/maxbogus/Repositories/hackathon
make check-all
docker compose build frontend
docker compose up -d frontend

curl -sS http://localhost:5173/ -o /dev/null -w 'HTTP %{http_code}\n'
curl -sS 'http://localhost:5173/api/v1/historical/export.csv' | head -2
curl -sS 'http://localhost:5173/api/v1/predictions/export.csv' | wc -l

# Ledger
# добавить F-099 + D-037

# HANDOFF.md, STATUS.md
# переместить тикеты в archive/

git add docs/backlog/STATUS.md docs/HANDOFF.md docs/ledger/
git commit -m "chore(handoff): T-220..T-224 integration done (F-099, D-037)"
```

## Manual Browser Test

Открыть `http://localhost:5173/passenger` в браузере. Проверить:
- [ ] Слева вверху: «Transit-AI — Прогноз трамвайного трафика Москвы»
- [ ] Секция «Фактическая нагрузка (факт за 2025-10-31)» — карточки с SUM
- [ ] Секция «Прогнозируемая нагрузка (прогноз за 2025-12-31)» — карточки с SUM
- [ ] Секция «Данные (~7583 строк)» — TanStack Table с фильтром, сортировкой
- [ ] Footer: «Модель: Базовая v1 · Точность (WAPE): 0.9272 · Обновлено только что» (T-231)

## F-099 (findings)

```json
{"id": "F-099", "ts": "<now>",
 "title": "AVG(value) в /predictions/load даёт среднее за час, не сумму за день",
 "context": "PassengerMode показывал 1007 для route 1 (среднее за час), вводило в заблуждение.",
 "evidence": "psql: AVG(value)=1007, SUM(value)/COUNT(DISTINCT date)=14096 для route 1",
 "impact": "Полная переделка PassengerMode — теперь CSV-таблица + SUM за день",
 "tickets": ["T-220","T-221","T-222","T-223","T-224"],
 "tags": ["frontend","passenger","ui","metric","bug"]}
```

## D-037 (decisions)

```json
{"id": "D-037", "ts": "<now>",
 "title": "PassengerMode показывает SUM за день из CSV вместо AVG из /predictions/load",
 "context": "AVG вводит в заблуждение (час vs день). Пользователь требует «как есть» — сырые CSV-данные.",
 "decision": "3 секции: факт (LastDayCard, SUM за MAX actuals date) + прогноз (SUM за MAX predictions date) + TanStack Table со всеми строками",
 "alternatives": ["Оставить AVG (отклонено: вводит в заблуждение)", "Backend считает SUM за день (отклонено: YAGNI, frontend может сам)"],
 "consequences": ["+ Пассажир видит реалистичные числа", "+ Таблица — drill-down для деталей", "+ TanStack фильтры из коробки", "- Виртуализация обязательна для 14k строк"],
 "tickets": ["T-220","T-221","T-222","T-223"],
 "tags": ["frontend","passenger","ui"]}
```
