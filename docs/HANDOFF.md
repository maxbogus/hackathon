# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T00:15:03.212665+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Продолжить разработку скелета Transit-AI

## Прогресс

Phase 0 (toolchain + clinerules + ledger)

## Git state

```
commit: 05a5c75
status: clean
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-037-ml-transit_ai-reports-plots-matplotlib-confusion-c.md
- T-039-ml-scripts-benchmark_baseline.py-+-benchmark_all.p.md
- T-042-apps-backend-get-api-v1-predictions-stop-id-route-id.md
- T-091-fix-mypy-exclude-regex-f-001.md
- T-133-slide-pain-points-to-solution-mapping-for.md

## Архив (done за всё время): 32

- T-037-ml-transit_ai-reports-plots-matplotlib-confusion-c.md
- T-039-ml-scripts-benchmark_baseline.py-+-benchmark_all.p.md
- T-042-apps-backend-get-api-v1-predictions-stop-id-route-id.md
- T-091-fix-mypy-exclude-regex-f-001.md
- T-133-slide-pain-points-to-solution-mapping-for.md
_(показаны последние 5 из 32)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-007**: Удалить T-116, отложить T-115 и T-130 до появления реальных данных
- **D-008**: Удалить мёртвые ссылки на несуществующие тикеты T-098/T-094/T-047/T-131-ui/T-117
- **D-009**: Отказаться от Streamlit UI, переписать T-129/T-130 под React/Vite (apps/frontend)

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
