# Backlog Format — YAML Frontmatter Spec

Все тикеты в `docs/backlog/tickets/*.md` начинаются с YAML frontmatter (`---`).
Pre-commit hook валидирует поля `id`, `status`, `phase`. Cline ДОЛЖЕН прочитать
эту спецификацию перед созданием тикета.

## Расположение файлов

- Один тикет = один файл.
- Именование: `docs/backlog/tickets/T-NNN-short-slug.md` (например `T-042-predictions-endpoint.md`).
- Фазы: `0` (toolchain), `1` (backend), `2` (ml), `3` (backend↔ml), `4` (frontend),
  `5` (assistant), `6` (mcp), `7` (docs), `8` (ci).

## Required Fields

```yaml
---
id: T-042                       # Unique ID, pattern: ^T-\d{3,}$
phase: 1                        # 0..8
title: Predictions endpoint     # Short, imperative
priority: P0                    # P0 (blocker) | P1 (critical) | P2 (improvement)
effort: 4                       # Person-hours (integer)
unit: hours                     # hours
rice:
  R: 3                          # Reach (integer)
  I: 2                          # Impact (0.25 | 0.5 | 1 | 2 | 3)
  C: 0.5                        # Confidence (0..1)
  score: 0.75                   # computed: R * I * C / effort
depends_on: [T-020, T-038]      # List of T-IDs
blocks: []                      # What this blocks
tags: [backend, api]
status: ready                   # backlog | ready | in-progress | blocked | done
created: 2026-09-20             # ISO date
updated: 2026-09-20             # ISO date (обновлять при изменении)
assignee: ""                    # Optional: кто делает
---

## Context

Why this task exists.

## Acceptance Criteria

- [ ] criterion 1
- [ ] criterion 2

## Technical Notes

Implementation hints.

## Verification

```bash
make api-gen
curl http://localhost:8000/api/v1/predictions/stop/42
# должен вернуть JSON с полями value, lower, upper, period_start, period_end
```

## Status

`ready` (по умолчанию) → `in-progress` (когда взял в работу) → `done` (после верификации)
```

## RICE Scoring

| Component | Question | Scale |
|---|---|---|
| R (Reach) | Сколько пользователей/сценариев покрыто | integer ≥0 |
| I (Impact) | Насколько критично для успеха хакатона | 0.25 / 0.5 / 1 / 2 / 3 |
| C (Confidence) | Уверенность в R и I | 0..1 |
| Effort | Человеко-часы | integer ≥1 |
| **Score** | `(R * I * C) / effort` | float |

Сортировка: `make backlog-ready` показывает топ-5 по score DESC.

## Status Lifecycle

```
backlog → ready → in-progress → done
                ↘ blocked → ready (после анблока)
```

## Workflow

1. Создать тикет: `make ticket ID=T-NNN TITLE="..."` (или вручную по шаблону)
2. Взять в работу: поменять `status: in-progress`
3. RED → GREEN → REFACTOR (см. `16-tdd-cycle.md`)
4. `make check-all`
5. Conventional Commit: `feat(backend): add predictions endpoint (T-042)`
6. Поменять `status: done`, поставить галочки в Acceptance Criteria
7. Переместить в `docs/backlog/archive/`
8. Обновить `docs/backlog/STATUS.md` (critical path)

## Ledger integration

Если RICE > 5 — добавить запись в `docs/ledger/decisions.jsonl` через `make ledger-add`.
Тег в JSON: `tickets: [T-042]`.
