---
id: T-141
phase: 4
title: "Frontend text registry (hybrid t(key)) — apps/frontend/src/lib/i18n/"
priority: P1
effort: 2.5
unit: hours
rice:
  R: 3
  I: 1.0
  C: 1.0
  score: 1.2
depends_on: []
blocks: [T-135]
tags: [frontend, i18n, refactoring, hackathon]
status: done
created: 2026-09-23
updated: 2026-09-23
assignee: "baev"
---

# T-141: Frontend text registry — гибридный t(key) с типизированным словарём

## Context

Все user-facing строки фронта (заголовки, кнопки, severity labels, рекомендации) сейчас хардкоднуты прямо в JSX (`App.tsx`, `components/Dispatcher/AlertCard.tsx`, `components/Dispatcher/AlertsPanel.tsx`, `pages/PassengerMode.tsx`). Это создаёт 4 проблемы:

1. **Переименование текста = правка N файлов** вместо 1.
2. **Нет типобезопасности** — опечатка в строке ловится только в рантайме.
3. **Невозможно подготовить к i18n** — если после хакатона проект пойдёт в open-source, добавить en-US будет = переписывание всех компонентов.
4. **Линтер не ловит хардкод** — ревью пропускает английский/русский прямо в JSX.

**Решение:** hybrid подход — на хакатоне `t(key)` = простой lookup из типизированного словаря `ru-RU.ts`, без библиотек. После хакатона — заменяем реализацию `t()` на `react-i18next`, **вызовы не меняются**.

**Паттерн подробно:** см. `.clinerules/20-text-constants-registry.md` (создан в этой сессии).

## Acceptance Criteria

- [x] `apps/frontend/src/lib/i18n/ru-RU.ts` — типизированный словарь со ВСЕМИ текущими UI-строками (app, dispatcher.alerts.*, passenger.recommendation.*, layout, и т.д.)
- [x] `apps/frontend/src/lib/i18n/keys.ts` — тип `TKey = Leaves<typeof TEXTS>` (рекурсивный dot-path)
- [x] `apps/frontend/src/lib/i18n/t.ts` — `t(key: TKey): string` + `tf(key: TKey, ...args): string`
- [x] `apps/frontend/src/lib/i18n/MIGRATION.md` — список: какой файл, какие ключи добавлены, в каком тикете
- [x] **Миграция существующего хардкода** (5 файлов):
  - [x] `apps/frontend/src/App.tsx` — mode-switcher, заголовки, role labels
  - [x] `apps/frontend/src/components/Dispatcher/AlertsPanel.tsx` — заголовки, empty state, lastUpdate
  - [x] `apps/frontend/src/components/Dispatcher/AlertCard.tsx` — severity labels (info/warning/critical), tram/capacity text
  - [x] `apps/frontend/src/pages/PassengerMode.tsx` — recommendation (go/wait/crowded), ETA labels
  - [x] `apps/frontend/src/lib/EtaCard.tsx` (UI-тексты — перенесены; `Alert.tsx` — не содержит хардкода UI literals)
- [x] **Тесты** `apps/frontend/src/lib/i18n/t.test.ts`:
  - [x] `t("dispatcher.alerts.title")` → возвращает русскую строку
  - [x] типобезопасность — `satisfies TKey` гарантирует проверку на этапе компиляции
  - [x] `tf("dispatcher.alerts.updatedAt", "13:30:00")` → `"обновлено: 13:30:00"`
  - [x] Snapshot всех текущих UI-строк (40+ keys exhaustively enumerated)
- [x] **CI gate**: `make frontend-text-check` (grep русских строк в `components/`, `pages/`, `App.tsx` вне `lib/i18n/`) — зелёный ✓
- [x] **Зарегистрировать в Makefile**:
  - [x] `frontend-text-check` — grep-guard
  - [x] `check-all` (обе цепочки) — добавил `frontend-text-check`
- [x] **Регрессия**: `yarn build` + `yarn test:run` (55/55 passed) + `yarn typecheck` зелёные

## Technical Notes

**Структура (из clinerule 20):**

```typescript
// apps/frontend/src/lib/i18n/ru-RU.ts
export const TEXTS = {
  app: {
    title: "Transit-AI — Прогноз трамвайного трафика Москвы",
    roleDispatcher: "Диспетчер",
    rolePassenger: "Пассажир",
  },
  dispatcher: {
    alerts: {
      title: "Перегруженные остановки",
      severityInfo: "Инфо",
      severityWarning: "Внимание",
      severityCritical: "Критично",
      emptyMessage: "Все остановки работают в штатном режиме",
      lastUpdate: (n: number) => `Обновлено ${n} сек назад`,
    },
  },
  passenger: {
    recommendation: {
      go: "Ехать сейчас",
      wait: (min: number) => `Подождать ${min} мин`,
      crowded: "Будет тесно",
    },
  },
} as const;
```

```typescript
// apps/frontend/src/lib/i18n/t.ts
import { TEXTS } from "./ru-RU";
import type { TKey } from "./keys";

export function t(key: TKey): string {
  const segments = key.split(".");
  let cur: any = TEXTS;
  for (const s of segments) cur = cur[s];
  return cur as string;
}

export function tf(key: TKey, ...args: unknown[]): string {
  const segments = key.split(".");
  let cur: any = TEXTS;
  for (const s of segments) cur = cur[s];
  return (cur as (...a: unknown[]) => string)(...args);
}
```

**Аудит хардкода (RED-фаза):**

```bash
grep -rEn '"[А-ЯЁа-яё][А-ЯЁа-яё]+[ А-ЯЁа-яё]*"' apps/frontend/src/components/ apps/frontend/src/pages/ apps/frontend/src/App.tsx 2>/dev/null | grep -v 'lib/i18n/' | grep -vE '(// |/\*|\* |\.test\.)'
```

**Алгоритм миграции (для каждого файла):**

1. Прочитать файл, выписать все хардкод-строки.
2. Сгруппировать по namespace (app/dispatcher/passenger/...).
3. Добавить в `ru-RU.ts` (с правильной структурой).
4. Заменить в JSX `>Перегруженные остановки<` → `>{t("dispatcher.alerts.title")}<`.
5. Если есть интерполяция `Обновлено ${n} сек назад` → `tf("dispatcher.alerts.lastUpdate", n)`.
6. Прогнать `yarn typecheck` — если TS падает, где-то не вынес ключ.
7. Прогнать тесты — поведение не должно поменяться.

## Verification

```bash
# 1. Структура создана
ls apps/frontend/src/lib/i18n/{ru-RU,keys,t}.ts
# OK

# 2. Тесты проходят
cd apps/frontend && yarn test:run src/lib/i18n/t.test.ts
# 4 passed

# 3. TypeScript зелёный
cd apps/frontend && yarn typecheck
# OK

# 4. Хардкод отсутствует
make frontend-text-check
# OK: No hardcoded UI strings

# 5. Сборка работает
cd apps/frontend && yarn build
# OK

# 6. Визуальная регрессия (для демо жюри)
yarn dev &
# Открыть http://localhost:5173, проверить:
# - Dispatcher mode: «Перегруженные остановки», «Инфо/Внимание/Критично»
# - Passenger mode: «Ехать сейчас», «Подождать N мин»
```

## Affected files (миграция)

| Файл | Хардкод → ключи |
|---|---|
| `App.tsx` | `app.title`, `app.roleDispatcher`, `app.rolePassenger` |
| `components/Dispatcher/AlertsPanel.tsx` | `dispatcher.alerts.title`, `.emptyMessage`, `.lastUpdate` |
| `components/Dispatcher/AlertCard.tsx` | `dispatcher.alerts.severityInfo`, `.severityWarning`, `.severityCritical` |
| `pages/PassengerMode.tsx` | `passenger.recommendation.go`, `.wait`, `.crowded` |
| `lib/Alert.tsx` / `lib/EtaCard.tsx` | (TBD — посмотреть в реализации) |

## Dependencies

- **Зависит от:** ничего (можно делать параллельно с T-115).
- **Блокирует:** T-135 (TanStack Router URL routing) — если роутер будет показывать route names в UI, нужно сначала заложить ключи.

## ADR

Записать в ledger как `D-NNN: hybrid t(key) text registry без библиотек` (RICE 6+).

## Не делать

- Не подключать `react-i18next`/`react-intl` до завершения хакатона (R6: time limits).
- Не делать `t()` для backend (`apps/backend/app/`).
- Не делать `t()` для тестов (fixtures/expect — напрямую).
- Не переименовывать существующие хардкод-строки в `ru-RU.ts` без апдейта вызывающего файла в том же коммите.

## Beneficiary Impact

- **Команда** (⭐⭐⭐⭐) — единая точка правды, проще ревью, проще перевод.
- **Жюри** (⭐⭐) — UI выглядит «production-ready» (стандартный паттерн i18n).
- **Open-source** (⭐⭐⭐⭐⭐) — готово к en-US добавлению после хакатона.

RICE: 1.20 — средний приоритет, но **P1** (качество UI перед демо).
