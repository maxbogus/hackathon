# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-22T20:48:20.540895+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Продолжить разработку скелета Transit-AI

## Прогресс

Phase 0 (toolchain + clinerules + ledger)

## Git state

```
commit: f820028
status: M docs/backlog/tickets/T-033-ml-transit_ai-training-predict.py-+-scripts-predic.md
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-032-ml-transit_ai-training-train.py-+-scripts-train_ba.md
- T-035-ml-transit_ai-training-evaluate.py-metrics-rmsle-m.md
- T-039-ml-scripts-benchmark_baseline.py-+-benchmark_all.p.md
- T-042-apps-backend-get-api-v1-predictions-stop-id-route-id.md
- T-091-fix-mypy-exclude-regex-f-001.md

## Архив (done за всё время): 28

- T-032-ml-transit_ai-training-train.py-+-scripts-train_ba.md
- T-035-ml-transit_ai-training-evaluate.py-metrics-rmsle-m.md
- T-039-ml-scripts-benchmark_baseline.py-+-benchmark_all.p.md
- T-042-apps-backend-get-api-v1-predictions-stop-id-route-id.md
- T-091-fix-mypy-exclude-regex-f-001.md
_(показаны последние 5 из 28)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-004**: Knowledge Capture: ledger + handoff + promotion
- **D-005**: Переиспользование кода из contest/ecup26-user-value
- **D-006**: Metrics (RMSLE/MAE/MAPE) moved to transit_ai.reports.metrics (single source of truth)

## Последние находки

- **F-002-resolved**: F-002 resolved: api-gen scripts created in commit acedb28
- **F-003**: T-042 and T-091 marked status:done but never git-mv'd to archive/
- **F-003-resolved**: F-003 resolved: T-042 and T-091 moved to archive/ in commit acedb28

## Открытые вопросы

(заполняется вручную или через `make ledger-add` с тегом `open-question`)

## Артефакты на диске

- `docs/ledger/decisions.jsonl` — решения (RICE > 5)
- `docs/ledger/findings.jsonl` — находки
- `docs/api/openapi.json` — генерируется backend (`make api-gen`)
- `apps/frontend/src/generated/` — Orval-генерация (`make fe-gen`)
- `ml/artifacts/` — обученные модели (gitignored)
- `predictions/` — прогнозы (gitignored)

## Не делать в следующей сессии

- ❌ Не патчить сгенерированные файлы в `apps/frontend/src/generated/`
- ❌ Не коммитить `.env`, `ml/artifacts/`, `predictions/`, `data/`
- ❌ Не использовать `npm install` или `pnpm install`
- ❌ Не читать `yarn.lock` / `uv.lock` в контекст
- ❌ Не пропускать pre-commit hook без причины
