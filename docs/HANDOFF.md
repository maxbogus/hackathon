# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-20T11:57:47.991890+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Продолжить разработку скелета Transit-AI

## Прогресс

Phase 0 (toolchain + clinerules + ledger)

## Git state

```
commit: 134def7
status: M Makefile
 M docs/HANDOFF.md
 M scripts/update_handoff.py
?? text.md
?? "\320\242\320\265\321\205\320\275\320\270\321\207\320\265\321\201\320\272\320\276\320\265 \320\267\320\260\320\264\320\260\320\275\320\270\320\265 (\320\242\320\227) \320\275\320\260 \321\200\320\260\320\267\321\200\320\260\320\261\320\276\321\202\320\272\321\203 \321\201\320\270\321\201\321\202\320\265\320\274\321\213 \320\277\321\200\320\276\320\263\320\275\320\276\320\267\320\270\321\200\320\276\320\262\320\260\320\275\320\270\321\217 \320\277\320\260\321\201\321\201\320\260\320\266\320\270\321\200\320\276\320\277\320\276\321\202\320\276\320\272\320\260 \321\202\321\200\320\260\320\274\320\262\320\260\320\265\320\262 \320\234\320\276\321\201\320\272\320\262\321\213.pdf"
```

## Что в работе (0)

_пусто_

## Что сделано (1)

- T-042-apps-backend-get-api-v1-predictions-stop-id-route-id.md

## Архив (done за всё время): 20

- T-020-apps-backend-get-api-v1-healthz-version-readyz.md
- T-024-ml-transit_ai-data-base-abc-datasource-contract.md
- T-025-ml-transit_ai-data-synthetic-800-stops-40-routes-2.md
- T-027-ml-transit_ai-models-baseline-mean-predictor.md
- T-031-ml-transit_ai-training-registry-meta.json-artifact.md
_(показаны последние 5 из 20)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-003**: MapProvider Strategy: OSM ↔ Yandex через env
- **D-004**: Knowledge Capture: ledger + handoff + promotion
- **D-005**: Переиспользование кода из contest/ecup26-user-value

## Последние находки

- **F-001**: pyproject.toml mypy exclude has invalid regex pattern

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
