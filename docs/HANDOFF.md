# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T03:22:00Z
> Обновлено: Cline после T-130 (recommend() pure function)

## Цель

Продолжить MVP для демо жюри: пассажирский режим + диспетчерские алерты + production README.

## Git state

```
commit: fd19d38 (HEAD)
status: clean
ahead of origin/master: +20 commits
```

## Что сделано (6)

- T-130 — recommend() бизнес-логика для passenger mode (1h, 97% test coverage) ✨ новый
- T-133 — слайд «Боли пассажиров → наше решение» (1h)
- T-042 — backend GET /api/v1/predictions/stop/{id}/route/{id} (3h)
- T-091 — fix mypy exclude regex (F-001)
- T-039 — ml benchmark scripts + api-gen scripts (5h)
- T-037 — ml reports/plots.py matplotlib headless Agg (3h)

## Архив (done за всё время): 33

## Следующая задача

**T-129:** React-режим «Пассажир» — role-switcher + selector остановки + 3 карточки ETA + интеграция `recommend()` через `<Alert severity={r.severity}>`.

Команда запуска:
```bash
cd apps/frontend
yarn dev   # затем переключить в "🧍 Пассажир", выбрать остановку 1
```

> T-130 уже подготовил API: `import { recommend, type ETAPrediction } from '@/lib/recommend';`
> Mock-данные для ETA кладутся в `src/mocks/eta_predictions.json` при `VITE_USE_MOCK=1`.

## Открытые вопросы

- (нет)

## Артефакты на диске

- `apps/frontend/src/lib/recommend.ts` — pure function (147 строк, 9 AC, 8 unit-tests)
- `apps/frontend/src/lib/recommend.test.ts` — vitest coverage 97.1% statements
- `apps/frontend/.yarnrc.yml` — nodeLinker: node-modules (D-010)
- `apps/frontend/yarn.lock` — зафиксирован (205 packages)
- `docs/ledger/decisions.jsonl` — D-001..D-010
- `docs/ledger/findings.jsonl` — F-001..F-007

## Последние решения в ledger

- **D-008**: Удалены мёртвые ссылки на T-098/T-094/T-047/T-131-ui/T-117
- **D-009**: Отказ от Streamlit UI → React/Vite (apps/frontend)
- **D-010**: nodeLinker=node-modules для apps/frontend (фикс EBADF под vitest@2)

## Последние находки

- **F-007**: .gitignore `lib/` тихо гасил apps/frontend/src/lib/. Фикс: закреплено как `/lib/`.

## Не делать в следующей сессии

- ❌ Не патчить сгенерированные файлы в `apps/frontend/src/generated/`
- ❌ Не коммитить `.env`, `node_modules/`, `coverage/`, `.yarn/cache`
- ❌ Не использовать `npm install` или `pnpm install` (только yarn 4 + nodeLinker)
- ❌ Не читать `yarn.lock` / `uv.lock` в контекст
- ❌ Не пытаться переключить frontend обратно на Yarn 4 PnP (D-010 зафиксировал nodeLinker)
