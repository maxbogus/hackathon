---
id: T-129
phase: 4
title: frontend режим «Пассажир» — прогноз ETA + загрузки для следующих рейсов (React/Vite)
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.9
  score: 13.5
depends_on: [T-019]
blocks: []
tags: [frontend, react, passenger, beneficiary]
status: done
created: 2026-09-23
updated: 2026-09-23
assignee: "baev"
---

# T-129: frontend режим «Пассажир» — прогноз ETA + загрузки для следующих рейсов (React/Vite)

## Context

Главный бенефициар хакатона — пассажиры московского трамвая (Ликсутов: «повышение качества
и безопасности поездок миллионов пассажиров»). Их главные боли:

- «Когда приедет трамвай?» (непредсказуемость интервалов)
- «Будет ли место?» (переполненность в час пик)

Режим «Пассажир» — отдельный UX, решающий именно боли пассажира. Включён в общий
дашборд как одна из ролей (Пассажир / Диспетчер / Аналитик / Планировщик).

**Архитектурное решение (D-009):** реализация на React/Vite в `apps/frontend/src/`,
а не на Streamlit. Streamlit не используется в проекте (apps/frontend на Vite 5 +
React 18 + TS strict, типизация через Orval из docs/api/openapi.json).

## Acceptance Criteria

- [x] В `apps/frontend/src/App.tsx` (или роутере) добавлен role-switcher: « Пассажир / 🎛️ Диспетчер / 📊 Аналитик / 🔮 Планировщик»
- [x] Компонент `apps/frontend/src/pages/PassengerMode.tsx` (или аналог)
- [x] selectbox со списком остановок (из `GET /api/v1/stops` — Orval hook)
- [x] При выборе остановки отображается 3 карточки ближайших рейсов (ETA + прогноз загрузки)
- [x] Цвет карточки зависит от загрузки: green (<60%), yellow (60-85%), red (>85%)
- [x] Использует mock-данные из `apps/frontend/src/mocks/eta_predictions.json` при `VITE_USE_MOCK=1`
- [x] Переключается на реальный API при `VITE_USE_MOCK=0` (через TanStack Query + Orval hook)
- [x] TypeScript strict: `npx tsc --noEmit` без ошибок
- [x] Smoke test в dev: `yarn dev` → переключить в режим "Пассажир", выбрать остановку 1 → 3 карточки

## Technical Notes

Файлы:
- `apps/frontend/src/pages/PassengerMode.tsx` — основной компонент
- `apps/frontend/src/lib/etaCard.tsx` — карточка рейса (цвет + ETA + load)
- `apps/frontend/src/mocks/eta_predictions.json` — mock fixture
- TanStack Query: `useQuery({ queryKey: ['eta', stopId], queryFn: getEtaForStop })` с `refetchInterval: 60_000`

Контракт API (после T-127): `GET /api/v1/predictions/eta?stop_id=X&n=3`. Orval сгенерирует
типизированный hook `useGetPredictionsEta(...)` в `apps/frontend/src/generated/`.

Цветовая шкала (см. T-128): green <70%, yellow 70-90%, red 90-110%, dark_red >110%.

## Verification

```bash
cd apps/frontend
VITE_USE_MOCK=1 yarn dev
# В браузере: переключить в режим "Пассажир", выбрать остановку 1
# Должно появиться 3 карточки с ETA и загрузкой (mock данные)

VITE_USE_MOCK=0 yarn dev  # когда API готов
```

## Beneficiary Impact

**Пассажиры (⭐⭐⭐⭐⭐)** — прямо решает боль «когда приедет и будет ли место».
**Департамент транспорта** — демонстрирует customer-centric подход, готовность к внедрению
в пассажирские приложения (Яндекс.Транспорт, mos.ru).

RICE: 13.5 — **топ-3 приоритет**, выше чем backend ML (T-019 = 6.75).
