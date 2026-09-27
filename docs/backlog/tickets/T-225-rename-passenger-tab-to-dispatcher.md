---
id: T-225
phase: 4
title: Переименовать «Пассажир» → «Диспетчер» в nav, убрать /dispatcher
priority: P2
effort: 1
unit: hours
rice:
  R: 1
  I: 1
  C: 0.9
  score: 0.9
depends_on: []
blocks: []
tags: [frontend, ux, rename]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

По запросу пользователя 2026-09-27 (mini-session): единственная «рабочая» вкладка
для оператора называлась «🧍 Пассажир», а вторая orphan-вкладка `/dispatcher`
(AlertsPanel) — «🎛️ Диспетчер». На демо жюри это выглядит странно, потому что
«Пассажир» — это и есть основной экран диспетчера (нагрузка по линиям + отклонение).
Решено: переименовать `/passenger` в «Диспетчер», `/dispatcher` убрать из nav
(orphan-роут сохранить для возможного возврата).

## Acceptance Criteria

**Frontend (правки):**
- [x] `apps/frontend/src/lib/roles.ts`: запись `dispatcher` удалена из `ROLES`, emoji у `passenger` → `🎛️`
- [x] `apps/frontend/src/lib/i18n/ru-RU.ts`: `app.rolePassenger.label` → `'Диспетчер'`, блок `app.roleDispatcher` удалён (orphan)
- [x] `apps/frontend/src/lib/roles.ts`: union-тип `RoleId` сужен до `'passenger' | 'analyst'` (dispatcher удалён из nav)
- [x] `apps/frontend/src/routes/__root.tsx`: обновить header-комментарий (нет упоминания `dispatcher`)
- [x] `apps/frontend/src/routes/dispatcher.tsx`: **НЕ трогаем** (orphan) — только комментарий

**Тесты (обновить, чтобы остались зелёными):**
- [x] `App.test.tsx`: убрать проверку `/пассажир/i`, добавить проверку «диспетчер» (на `/passenger`)
- [x] `routes/-__root.test.tsx`: тест «renders three role links» → переписать на «two role links (passenger + analyst)», убрать упоминание `/dispatcher` в hrefs. Тест про `/dispatcher` outlet **оставлен** (orphan-роут рендерит AlertsPanel по прямой ссылке — это полезно для дебага и не ломается).
- [x] `lib/i18n/t.test.ts`: тест `returns the role labels` → `app.rolePassenger.label === 'Диспетчер'`, убрано упоминание `app.roleDispatcher`. Snapshot `sampleKeys` — убрано `app.roleDispatcher.label/description`.

**Verification:**
- [x] `yarn typecheck` — 0 errors в моих файлах (2 pre-existing в `routeCsv.ts` — не моя зона)
- [x] `yarn test:run` — 26/26 в моих файлах, 149/151 всего (2 pre-existing failures в `routeCsv.test.ts` — T-221)
- [x] `yarn lint` — 0 issues в моих файлах (6 pre-existing в `downloadCsv.ts`, 2 warnings в `HorizonToggle.tsx`)
- [x] `make frontend-text-check` (grep) — без хардкода
- [x] Визуально (через `yarn dev`): на `/` редирект на `/passenger`, в nav 2 ссылки — 🎛️ Диспетчер (active) и 📊 Аналитик (подтверждено по тестам + ручной проверке DOM)
- [x] Прямая ссылка `/dispatcher` всё ещё работает (orphan, рендерит AlertsPanel — тест `'renders the dispatcher alerts panel at /dispatcher'` остался зелёным)

**Knowledge:**
- [x] `docs/HANDOFF.md` обновлён (mini-session 2026-09-27T13:30:00Z)
- [x] `apps/frontend/src/lib/i18n/MIGRATION.md` — строка для T-225 добавлена
- [x] Ledger: F-098 в `findings.jsonl`, D-037 в `decisions.jsonl`

## Technical Notes

**Минимально-инвазивный подход:** не переименовываем ключ `app.rolePassenger` в
`app.roleDispatcher` (это бы сломало кучу тестов). Вместо этого **меняем содержимое**
блока `app.rolePassenger` (label → «Диспетчер»), а emoji меняем в `roles.ts`.
Файлы под `passenger.*` namespace (включая `passenger.modeTitle = '🧍 Пассажир — ...'`)
**не трогаем** — заголовок страницы остаётся «Пассажир — нагрузка по линиям»
(это название дашборда, не роль в nav).

**Почему оставляем `roleDispatcher` блок в `ru-RU.ts` удалённым:** после удаления
записи `dispatcher` из `ROLES` этот ключ становится мёртвым — TypeScript не упадёт
(tests не проверяют его напрямую кроме snapshot), но `eslint`-dead-code может
ругнуться. Чище удалить.

**Почему `/dispatcher` оставляем как orphan:** T-131 (AlertsPanel) — реальный код,
может пригодиться для дебага, удалять — потеряем функциональность без выигрыша.
TanStack Router автоматически его не подхватит (нет ссылки из nav), но прямой URL
продолжит работать.

## Verification

```bash
# 1. Typecheck
cd apps/frontend && yarn typecheck

# 2. Tests
cd apps/frontend && yarn test:run

# 3. Lint
cd apps/frontend && yarn lint

# 4. Visual
cd apps/frontend && yarn dev
# Открыть http://localhost:5173/ → редирект на /passenger
# В nav должно быть: [🎛️ Диспетчер (active)] [📊 Аналитик]
# Перейти на /analyst — там остаётся активной Аналитик
# Перейти на /dispatcher — orphan-роут, рендерит AlertsPanel (но из nav не доступен)
```

## Status

`in-progress` (2026-09-27, после Act mode)
