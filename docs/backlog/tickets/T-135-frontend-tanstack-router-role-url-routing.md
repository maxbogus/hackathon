---
id: T-135
phase: 4
title: "apps/frontend — TanStack Router: перевести role-switcher на URL (/passenger, /dispatcher, /analyst, /planner)"
priority: P1
effort: 2
unit: hours
rice:
  R: 4
  I: 3.0
  C: 1.0
  score: 6.0
depends_on: [T-129]
blocks: []
tags: [frontend, routing, tanstack, beneficiary, hackathon, mvp]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "baev"
---

# T-135: TanStack Router URL routing для role-switcher

## Context

Сейчас `apps/frontend/src/App.tsx` использует **локальный `useState<Role>`** для переключения
ролей (Passenger / Dispatcher / Analyst / Planner). Это означает:
1. Нельзя дать ссылку коллеге «открой режим Диспетчер» — состояние теряется при reload.
2. Browser back/forward не работает — кнопка «Назад» не переключает роль.
3. Deep linking невозможен — `http://localhost:5173` всегда открывает Passenger по умолчанию.
4. Жюри не может сразу открыть «нужный» режим для демо конкретного сценария.

F-009 в findings уже зафиксировал проблему (`prettier-plugin-organize-imports` и связанные
нюансы), и в `App.tsx` есть TODO: «routing is intentionally trivial (useState) until TanStack
Router file-based routes land».

HANDOFF.md и STATUS.md уже **обещают этот тикет** (T-135) в очереди после T-131 — но файла
тикета не было. Этот тикет закрывает обещание.

## Acceptance Criteria

- [ ] Установлен `yarn workspace @transit-ai/frontend add @tanstack/react-router`
- [ ] Установлен `@tanstack/router-plugin` для Vite (`yarn add -D @tanstack/router-vite-plugin`)
- [ ] В `vite.config.ts` подключён router plugin
- [ ] Создан `apps/frontend/src/routes/__root.tsx` (уже есть для TanStack Router plugin, F-009)
- [ ] Созданы 4 file-based маршрута:
  - `apps/frontend/src/routes/passenger.tsx` → `<PassengerMode />`
  - `apps/frontend/src/routes/dispatcher.tsx` → `<AlertsPanel />`
  - `apps/frontend/src/routes/analyst.tsx` → `<PlaceholderPanel role="analyst" />`
  - `apps/frontend/src/routes/planner.tsx` → `<PlaceholderPanel role="planner" />`
  - `apps/frontend/src/routes/index.tsx` → redirect на `/passenger`
- [ ] `App.tsx` переписан: вместо `useState<Role>` — `<Outlet />` из router, role-switcher в header
  использует `<Link to="/dispatcher">` (нативная навигация)
- [ ] URL `/passenger` открывает PassengerMode по умолчанию
- [ ] URL `/dispatcher` открывает AlertsPanel
- [ ] Browser back/forward работает корректно
- [ ] При перезагрузке страницы остаёмся на текущей роли
- [ ] `routeTree.gen.ts` регенерируется автоматически (router plugin)
- [ ] Тест: `apps/frontend/src/App.test.tsx` обновлён — проверяет навигацию через `<Link>`
- [ ] `yarn typecheck` без ошибок
- [ ] `yarn build` собирает

## Technical Notes

Структура файлов:
```
apps/frontend/src/
├── App.tsx                         # переписан: <Outlet/>, без useState
├── main.tsx                        # без изменений (router подключается в plugin)
├── routeTree.gen.ts                # авто-генерируется plugin
├── routes/                         # новая папка
│   ├── __root.tsx                  # root layout с header + <Outlet/>
│   ├── index.tsx                   # redirect → /passenger
│   ├── passenger.tsx               # <PassengerMode />
│   ├── dispatcher.tsx              # <AlertsPanel />
│   ├── analyst.tsx                 # <PlaceholderPanel role="analyst" />
│   └── planner.tsx                 # <PlaceholderPanel role="planner" />
└── components/Dispatcher/...       # без изменений
```

Header с role-switcher (новая версия App.tsx):
```tsx
import { Link, useRouterState } from '@tanstack/react-router';

export function App(): JSX.Element {
  const { location } = useRouterState();
  const activeRole = location.pathname.split('/')[1] || 'passenger';

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      <header>
        <h1>Transit-AI</h1>
        <nav>
          {ROLES.map((r) => (
            <Link
              key={r.id}
              to={`/${r.id}`}
              data-active={activeRole === r.id}
              aria-pressed={activeRole === r.id}
            >
              {r.emoji} {r.label}
            </Link>
          ))}
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
```

**Важно (F-009):** НЕ удалять `src/routes/__root.tsx` — TanStack Router plugin требует его.

## Verification

```bash
# 1. Установка зависимостей
cd apps/frontend && yarn install

# 2. Type-check
cd apps/frontend && yarn typecheck
# Ожидаем: 0 errors

# 3. Build
cd apps/frontend && yarn build
# Ожидаем: dist/ собран

# 4. Tests
cd apps/frontend && yarn test --run App
# Ожидаем: тесты навигации зелёные

# 5. Live smoke
cd apps/frontend && yarn dev
# Открыть http://localhost:5173/dispatcher
# Ожидаем: открывается AlertsPanel
# Reload страницы → остаёмся на /dispatcher
# Browser back → переходим на /passenger (если до этого были там)
```

## Beneficiary Impact

**Жюри (⭐⭐⭐⭐)** — ссылка `localhost:5173/dispatcher` сразу открывает нужный режим для демо.
**UX (⭐⭐⭐)** — back/forward и reload работают как ожидается.
**Девопс/QA (⭐⭐⭐)** — можно тестировать отдельные режимы через URL без programmatic переключения.

RICE: 6.0 — топ-7 приоритет. Делается в Фазе 4 после T-129.
