# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-23T03:55:00Z
> Обновлено: Cline после T-129 (PassengerMode UI)

## Цель

Продолжить MVP для демо жюри: пассажирский режим + диспетчерские алерты + production README.

## Git state

```
commit: ff4ac43 (предыдущий HEAD)
status: clean (до T-129)
ahead of origin/master: +20 commits
```

После T-129 будет +2 коммита (feat + chore).

## Что сделано (7)

- T-129 — React/Vite режим «Пассажир» с ETA + load + рекомендация (1h, 35 tests) ✨ новый
- T-130 — recommend() pure function для passenger mode (1h, 97% test coverage)
- T-133 — слайд «Боли пассажиров → наше решение» (1h)
- T-042 — backend GET /api/v1/predictions/stop/{id}/route/{id} (3h)
- T-091 — fix mypy exclude regex (F-001)
- T-039 — ml benchmark scripts + api-gen scripts (5h)
- T-037 — ml reports/plots.py matplotlib headless Agg (3h)

## Архив (done за всё время): 34

## Что в работе

Пусто (T-129 только что завершён, готовы брать T-115 / T-128 / T-131 / T-127 / T-135).

## Следующая задача

**T-127:** Backend `/api/v1/predictions/eta?stop_id=X&n=3` — следующие N трамваев.

Команда запуска:
```bash
cd apps/backend
uv run pytest tests/test_eta_endpoint.py -v
make api-gen && make fe-gen  # чтобы Orval хук появился в src/generated/
```

> T-129 уже подготовил mock-режим, который автоматически переключится на реальный endpoint
> когда `VITE_USE_MOCK=0` + backend endpoint жив. До этого PassengerMode работает на моках.

## Открытые вопросы

- (нет)

## Артефакты на диске

### Frontend (T-129)
- `apps/frontend/src/App.tsx` — role-switcher (4 роли: passenger / dispatcher / analyst / planner)
- `apps/frontend/src/pages/PassengerMode.tsx` — главная страница пассажира
- `apps/frontend/src/lib/etaClient.ts` — pure data layer (mock/real switch через `VITE_USE_MOCK`)
- `apps/frontend/src/lib/Alert.tsx` — минимальный `<Alert severity>` без MUI
- `apps/frontend/src/lib/EtaCard.tsx` — карточка рейса (4 цветовых тира)
- `apps/frontend/src/lib/loadTier.ts` — load percentage → tier (green/yellow/red/darkred)
- `apps/frontend/src/mocks/{stops,eta_predictions}.json` — фикстуры для демо
- `apps/frontend/src/routes/__root.tsx` — TanStack Router placeholder (F-009)
- Тесты: 35 passed, coverage ~73% statements (PassengerMode 94%, EtaCard 100%, Alert 100%, loadTier 100%)

### Прочее
- `apps/frontend/src/lib/recommend.ts` — pure function (147 строк, 9 AC, 8 unit-tests)
- `apps/frontend/.yarnrc.yml` — nodeLinker=node-modules (D-010)
- `apps/frontend/.prettierrc.json` — без prettier-plugin-organize-imports (F-010)
- `apps/frontend/yarn.lock` — зафиксирован (206 packages после @testing-library/dom)
- `docs/ledger/decisions.jsonl` — D-001..D-010
- `docs/ledger/findings.jsonl` — F-001..F-008, F-009, F-010

## Последние решения в ledger

- **D-008**: Удалены мёртвые ссылки на T-098/T-094/T-047/T-131-ui/T-117
- **D-009**: Отказ от Streamlit UI → React/Vite (apps/frontend)
- **D-010**: nodeLinker=node-modules для apps/frontend (фикс EBADF под vitest@2)

## Последние находки

- **F-008**: .githooks/ не активирован → исправлено
- **F-009**: TanStack Router plugin требует `src/routes/__root.tsx` → создан placeholder
- **F-010**: .prettierrc.json ссылается на отсутствующий `prettier-plugin-organize-imports` → убран из конфига

## Не делать в следующей сессии

- ❌ Не патчить сгенерированные файлы в `apps/frontend/src/generated/`
- ❌ Не коммитить `.env`, `node_modules/`, `coverage/`, `.yarn/cache`
- ❌ Не использовать `npm install` или `pnpm install` (только yarn 4 + nodeLinker)
- ❌ Не читать `yarn.lock` / `uv.lock` в контекст
- ❌ Не пытаться переключить frontend обратно на Yarn 4 PnP (D-010 зафиксировал nodeLinker)
- ❌ Не добавлять `prettier-plugin-organize-imports` без надобности (F-010)
- ❌ Не удалять `src/routes/__root.tsx` — TanStack Router plugin требует его (F-009)
