---
id: T-129
phase: 0
title: streamlit режим Пассажир — прогноз ETA + загрузки для следующих рейсов
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.9
  score: 13.5
depends_on: [T-019, T-098]
blocks: [T-127, T-128]
tags: [frontend, streamlit, passenger, beneficiary]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "baev"
---

# T-129: streamlit режим «Пассажир» — прогноз ETA + загрузки для следующих рейсов

## Context

Главный бенефициар хакатона — пассажиры московского трамвая (Ликсутов: «повышение качества
и безопасности поездок миллионов пассажиров»). Их главные боли:

- «Когда приедет трамвай?» (непредсказуемость интервалов)
- «Будет ли место?» (переполненность в час пик)

Сейчас в плане 3 режима (Аналитик / Диспетчер / Планировщик). Этого мало — для пассажира
нужен отдельный UX, решающий именно его боли.

## Acceptance Criteria

- [ ] В sidebar Streamlit добавлен radio: «🧍 Пассажир / 🎛️ Диспетчер / 📊 Аналитик / 🔮 Планировщик»
- [ ] Режим «Пассажир» показывает selectbox со списком остановок (из /api/v1/stops)
- [ ] При выборе остановки отображается 3 карточки ближайших рейсов (ETA + прогноз загрузки)
- [ ] Цвет карточки зависит от загрузки: green (<60%), yellow (60-85%), red (>85%)
- [ ] Использует mock-данные при `USE_MOCK=1` (для параллельной разработки без API)
- [ ] Переключается на реальный API при `USE_MOCK=0`
- [ ] Работает в браузере без ошибок (smoke test)

## Technical Notes

Файл: `apps/streamlit_app/app.py`. Использует `streamlit`, `folium`, `streamlit-folium`,
`altair` (уже установлены). Компоненты: `st.radio`, `st.selectbox`, `st.metric`,
`st.columns(3)`, `st.markdown` для цветных карточек.

Mock fixture для режима «Пассажир»: `apps/streamlit_app/mock_data/eta_predictions.json`
(массив {stop_id, route_id, eta_min, predicted_load_pct, model_id}).

Использует контракт `GET /api/v1/predictions/eta?stop_id=X&n=3` (новый endpoint, добавить в T-019).

## Verification

```bash
USE_MOCK=1 streamlit run apps/streamlit_app/app.py
# В браузере: переключить в режим "Пассажир", выбрать остановку 1
# Должно появиться 3 карточки с ETA и загрузкой (mock данные)

USE_MOCK=0 streamlit run apps/streamlit_app/app.py  # когда API готов
```

## Beneficiary Impact

**Пассажиры (⭐⭐⭐⭐⭐)** — прямо решает боль «когда приедет и будет ли место».
**Департамент транспорта** — демонстрирует customer-centric подход, готовность к внедрению
в пассажирские приложения (Яндекс.Транспорт, mos.ru).

RICE: 13.5 — **топ-3 приоритет**, выше чем backend ML (T-019 = 6.75).
