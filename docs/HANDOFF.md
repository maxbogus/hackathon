# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-20T08:26:07.728399+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Завершить MVP скелет: backend (Phase 1) + ML pipeline (Phase 2) + frontend карта (Phase 4). Подготовить скелет к получению реальных данных от организаторов.

## Прогресс

Phase 0 (toolchain + clinerules + ledger + 13 тикетов) — ЗАВЕРШЕН. Phase 1-7 — в очереди.

## Git state

```
commit: cf9b826
status: M README.md
?? .clinerules/
?? .editorconfig
?? .env.example
?? .githooks/
?? .gitignore
?? .pre-commit-config.yaml
?? AGENTS.md
?? Makefile
?? apps/
?? data/
?? docs/
?? ml/
?? predictions/
?? pyproject.toml
?? scripts/
?? text.md
?? "\320\242\320\265\321\205\320\275\320\270\321\207\320\265\321\201\320\272\320\276\320\265 \320\267\320\260\320\264\320\260\320\275\320\270\320\265 (\320\242\320\227) \320\275\320\260 \321\200\320\260\320\267\321\200\320\260\320\261\320\276\321\202\320\272\321\203 \321\201\320\270\321\201\321\202\320\265\320\274\321\213 \320\277\321\200\320\276\320\263\320\275\320\276\320\267\320\270\321\200\320\276\320\262\320\260\320\275\320\270\321\217 \320\277\320\260\321\201\321\201\320\260\320\266\320\270\321\200\320\276\320\277\320\276\321\202\320\276\320\272\320\260 \321\202\321\200\320\260\320\274\320\262\320\260\320\265\320\262 \320\234\320\276\321\201\320\272\320\262\321\213.pdf"
```

## Что в работе (0)

_пусто_

## Что сделано (0)

_пусто_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-003**: MapProvider Strategy: OSM ↔ Yandex через env
- **D-004**: Knowledge Capture: ledger + handoff + promotion
- **D-005**: Переиспользование кода из contest/ecup26-user-value

## Последние находки

_пусто_

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
