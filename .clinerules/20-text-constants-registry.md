# 20-text-constants-registry.md — Текстовые константы фронта (hybrid t())

## Зачем

Все user-facing строки фронта (заголовки, кнопки, подсказки, severity labels, рекомендации) — **в одном месте**, типизированно, через единую сигнатуру `t(key)`.

**Цели:**
1. **Единая точка правды** — переименовал кнопку → поменял в `ru-RU.ts` → на всех страницах обновилось.
2. **Типобезопасность** — TypeScript падает на этапе компиляции, если ключ не существует.
3. **Готовность к i18n** — после хакатона, если нужно, заменяем реализацию `t()` на `react-i18next`, **вызовы не меняются**.
4. **Линтер-страховка** — grep в CI запрещает русский/UI строки прямо в `.tsx`.

**Решение (D-NNN):** гибрид с `t(key)` — `apps/frontend/src/lib/i18n/` с типизированным словарём, на хакатоне без библиотек.

## Структура

```
apps/frontend/src/lib/i18n/
├── ru-RU.ts         # словарь: const TEXTS = { dispatcher: { alerts: { title: "..." } } }
├── keys.ts          # export type TKey = keyof typeof TEXTS + helpers
├── t.ts             # export function t(key: TKey, vars?: Record<string, string | number>): string
└── MIGRATION.md     # лог миграций: какой файл, какие ключи добавлены
```

## Сигнатура

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
// apps/frontend/src/lib/i18n/keys.ts
import type { TEXTS } from "./ru-RU";

// Рекурсивный тип: "dispatcher.alerts.title" → string
type Join<K, P> = K extends string
  ? P extends string
    ? `${K}.${P}`
    : never
  : never;
type Leaves<T> = T extends object
  ? {
      [K in keyof T]: K extends string
        ? T[K] extends string
          ? K
          : Join<K, Leaves<T[K]>>
        : never;
    }[keyof T]
  : never;
export type TKey = Leaves<typeof TEXTS>;
```

```typescript
// apps/frontend/src/lib/i18n/t.ts
import { TEXTS } from "./ru-RU";
import type { TKey } from "./keys";

/** Получить локализованную строку по типизированному ключу. */
export function t(key: TKey): string {
  const segments = key.split(".");
  let cur: any = TEXTS;
  for (const s of segments) cur = cur[s];
  return cur as string;
}

/** Получить локализованную функцию-строку с подстановкой. */
export function tf(
  key: TKey,
  ...args: any[]
): string {
  const segments = key.split(".");
  let cur: any = TEXTS;
  for (const s of segments) cur = cur[s];
  return (cur as (...args: any[]) => string)(...args);
}
```

## Использование в компонентах

```typescript
// ПРАВИЛЬНО:
import { t, tf } from "@/lib/i18n/t";

export function AlertsPanel() {
  return (
    <div>
      <h2>{t("dispatcher.alerts.title")}</h2>
      <span>{tf("dispatcher.alerts.lastUpdate", 30)}</span>
    </div>
  );
}

// НЕПРАВИЛЬНО:
export function AlertsPanel() {
  return (
    <div>
      <h2>Перегруженные остановки</h2>     {/* хардкод — grep ругается */}
      <span>Обновлено 30 сек назад</span>   {/* хардкод */}
    </div>
  );
}
```

## Что НЕ идёт через t()

- **Console.error, throw, логи** — internal, не UI.
- **Тесты** — фикстуры не через `t()` (тестируем логику, не перевод).
- **Backend Pydantic message strings** — это в `apps/backend/app/schemas/`, не фронт.

## Миграция существующего кода

См. `apps/frontend/src/lib/i18n/MIGRATION.md`. Каждый тикет, который добавляет/правит UI-тексты, ОБЯЗАН:

1. Найти все хардкод-строки в правке (grep `[А-ЯЁа-яё]` в `.tsx`).
2. Добавить ключи в `ru-RU.ts` с типизированной структурой.
3. Заменить хардкод на `t(...)` / `tf(...)`.
4. Обновить `MIGRATION.md` (одна строка: `T-NNN: файл.tsx → keys: dispatcher.alerts.title`).

## CI gate (lint)

В `Makefile` → `make frontend-text-check`:

```bash
@grep -rEn '"[А-ЯЁа-яё][А-ЯЁа-яё]+[ А-ЯЁа-яё]*"' \
  apps/frontend/src/components/ apps/frontend/src/pages/ apps/frontend/src/App.tsx 2>/dev/null \
  | grep -v 'lib/i18n/' \
  | grep -vE '(// |/\*|\* |\.test\.)' \
  && echo "Хардкод русских строк в UI — используй t() из lib/i18n" \
  && exit 1 \
  || echo "No hardcoded UI strings"
```

(Greppable-вариант дешевле `eslint-plugin-i18next` и достаточен для хакатона.)

## Расширение после хакатона

Когда понадобится (open-source, международные пользователи):

1. `yarn workspace @transit-ai/frontend add react-i18next i18next`
2. Заменить `t.ts`:
   ```typescript
   import i18n from "i18next";
   import ruRU from "./ru-RU.json"; // переименовать ru-RU.ts → .json
   i18n.init({ resources: { "ru-RU": { translation: ruRU } }, lng: "ru-RU" });
   export const t = (key: TKey) => i18n.t(key);
   export const tf = (key: TKey, ...args: any[]) => i18n.t(key, ...args);
   ```
3. Все вызовы `t("...")` остаются как есть.
4. Добавить `en-US.json` — тот же shape, новые строки.

**Не нужно:** менять `keys.ts`, `ru-RU` структуру, типы, вызовы.

## Когда НЕ применять

- Не делаем `t()` для backend (`apps/backend/app/`).
- Не делаем `t()` для `apps/frontend/src/lib/*.ts` (pure logic, не UI).
- Не делаем `t()` для тестов (fixtures/expect — напрямую).
- Не превращаем в `react-intl`/`react-i18next` до завершения хакатона (R6: time limits).

## Cross-references

- Реализация: `docs/backlog/tickets/T-141-text-registry-i18n-hybrid.md`
- Миграция UI: см. `apps/frontend/src/lib/i18n/MIGRATION.md` после T-141
- ADR: `D-NNN` в `docs/ledger/decisions.jsonl`
