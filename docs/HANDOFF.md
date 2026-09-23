# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T12:19:44.673892+00:00
> Обновлено: автоматически через `make handoff-update`

## Цель

Track A: T-122 MapProvider (после T-142 config). Реальные данные ~27.09 → retrain → submission checklist T-137. Frontend infrastructure готов: T-141 (i18n), T-135 (router), T-142 (config).

## Прогресс

Phase 4 (frontend): T-135, T-141, T-142 DONE. Phase 0/1/2/3 готовы. Готовимся к Track A и T-137 submission.

## Git state

```
commit: d873866
status: R  docs/backlog/tickets/T-142-frontend-typed-config-with-stub-fallback.md -> docs/backlog/archive/T-142-frontend-typed-config-with-stub-fallback.md
```

## Что в работе (0)

_пусто_

## Что сделано (5)

- T-131-dispatcher-alerts-overload-predictions-15.md
- T-133-slide-pain-points-to-solution-mapping-for.md
- T-135-frontend-tanstack-router-role-url-routing.md
- T-141-frontend-text-constants-registry-hybrid.md
- T-142-frontend-typed-config-with-stub-fallback.md

## Архив (done за всё время): 40

- T-131-dispatcher-alerts-overload-predictions-15.md
- T-133-slide-pain-points-to-solution-mapping-for.md
- T-135-frontend-tanstack-router-role-url-routing.md
- T-141-frontend-text-constants-registry-hybrid.md
- T-142-frontend-typed-config-with-stub-fallback.md
_(показаны последние 5 из 40)_

## Следующая задача

Выбрать через `make backlog-ready` (топ-5 ready тикетов).

## Последние решения в ledger

- **D-013**: Dispatcher alerts polling: setInterval via TanStack Query refetchInterval, не streamlit-autorefresh
- **D-014**: Hybrid text registry t(key) без react-i18next на хакатоне
- **D-015**: Frontend config с stub-fallback вместо inline import.meta.env в каждом компоненте

## Последние находки

- **F-012**: T-122 RICE score в YAML (4.5) не сходится с формулой (2.70)
- **F-013**: yarn inside run_commands loses cwd between commands; use yarn --cwd <abs-path>
- **F-014**: jsdom window.scrollTo throws 'Not implemented' during TanStack Router navigation

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
