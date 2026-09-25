---
id: T-171
phase: 7
title: Deadline prep за 48 часов — final submission + 10-слайдовая презентация + deploy
priority: P0
effort: 12
unit: hours
rice:
  R: 10
  I: 3.0
  C: 1.0
  score: 2.50
depends_on: [T-168, T-149]
blocks: []
tags: [deadline, pitch, deploy, presentation, hackathon-final, 27-09]
status: in-progress
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-171: Deadline prep 48h — submission + pitch + deploy

## Context

Q-A сессия 25.09.2026 (F-043): **дедлайн 27.09.2026 23:59 MSK**. Это **воскресенье**,
а сейчас 25.09 22:00 → осталось **~48 часов**. Q&A больше проводиться не будет.

Также критично из Q-A:
- Q3, Q17: **только 9 маршрутов** (route 5 исключён — нет данных) — ИСПРАВЛЕНО в ml/scripts/make_submission.py (ROUTES = 9)
- Q18: **round to integer** — ИСПРАВЛЕНО (np.round(preds).astype(np.int64))
- Q22: pitch **5+5 минут** (5 мин выступление + 5 мин Q&A) — свободный формат
- Q15: интернет будет доступен у жюри при запуске сервиса
- Q9: интересно показать "восстановление пробелов" (тех. сбои, ремонты) — плюс к оценке
- Q23: long-term forecast — асинхронный (не блокирует short-term)

**Submission #9 готов** (xgboost_v8_poi, route 5 убран, integer rounding):
- 13176 строк (9 маршрутов × 61 день × 24 часа)
- Holdout WAPE-score = 0.8751 (calibrated, локально)

## Что осталось сделать за 48 часов

### A. Submission (за 1-2 часа)

- [ ] Залить `predictions/submission_xgboost_v8_poi_20251101_20251231_20260925T191625Z.csv` на платформу
- [ ] Залить manifest `.json` рядом (если платформа принимает)
- [ ] Подождать platform_score 1-5 мин
- [ ] Записать F-044 в ledger с drift = platform - 0.8751
- [ ] Если score > 0.73231 (baseline) — коммит + обновить best_so_far в STATUS.md

### B. Backend/Frontend deploy (за 2-4 часа)

- [ ] Проверить `make up` — docker compose запускается без ошибок
- [ ] Проверить endpoints:
  - GET /api/v1/predictions/stop/{id}  (T-127)
  - GET /api/v1/predictions/eta?stop_id=X&n=3 (T-127)
  - GET /api/v1/insights/alerts (T-131)
- [ ] Проверить frontend :5173:
  - Dashboard с графиками (T-141)
  - Dispatcher alerts panel (T-131)
  - Passenger mode с ETA + рекомендациями (T-129, T-130)
- [ ] Если есть external API ключи (Yandex Maps) — добавить в .env

### C. Презентация 10 слайдов (за 4-6 часов)

Акцент из Q22:
1. **Структура решения** — что сделали (backend + ml + frontend)
2. **Методы и подходы** — XGBoost + POI features + per-route bias + seasonal/weather/validators
3. **Технологическая архитектура** — FastAPI + Postgres+Timescale + Vite/React
4. **Проверочные достигнутые результаты** — holdout 0.8751, baseline improvement 5×

Структура слайдов:
1. Title (команда, проект, дата)
2. Проблема: прогноз пассажиропотока трамваев
3. Решение: предсказание по маршруту/дате/часу
4. ML pipeline: train → predict → submission
5. Фичи: seasonal + weather + validators + POI (146 объектов)
6. Метрика: WAPE-score = 1 - WAPE
7. Результаты: holdout 0.8751, baseline 0.73 (5× улучшение)
8. Frontend: диспетчер + пассажир режимы
9. Архитектура: backend + frontend + deploy
10. Демо + итоги + что дальше

### D. Auth + логин/пароль для жюри (за 1 час)

Из Q5, Q6: желательна базовая auth + файл с логином/паролем.
- Backend: simple API key check (header X-API-Key)
- Frontend: показать login form если нет ключа
- Файл: `JURY_ACCESS.md` с инструкцией + credentials

### E. Симуляция сбоев (за 2-3 часа, опционально)

Из Q9: "Интересно показать восстановление пробелов в данных (тех. сбои, ремонты, потеря связи оборудования). Это даст плюс к оценке."
- Synthetic slots в predictions для route_id × hour (несколько дней с пропусками)
- Восстановление через recursive forecast (T-153 retry) или XGBoost fallback
- Frontend: визуализация пробелов как "сбой оборудования"

### F. README + video (за 2-3 часа)

- [ ] README на русском (T-115 если ещё не сделано)
- [ ] docs/HACKATHON_CHECKLIST.md обновить
- [ ] Demo video 2-3 минуты (T-167 если сделано)
- [ ] Final commit + push

### G. Документация (за 1-2 часа)

- [ ] Обновить STATUS.md с финальными результатами
- [ ] Обновить HANDOFF.md (финальная версия)
- [ ] Обновить docs/ledger/decisions.jsonl (если были ADR)

## Acceptance Criteria

- [ ] Submission #9 залит на платформу
- [ ] F-044 в ledger с platform_score + drift
- [ ] `make up` запускает docker compose без ошибок
- [ ] `/api/v1/predictions/eta` отвечает 200
- [ ] Frontend показывает dispatcher + passenger режимы
- [ ] 10 слайдов презентации готовы
- [ ] README + JURY_ACCESS.md в репо
- [ ] Все commits сделаны

## Verification

```bash
# Submission
make up
make submission  # или ручной вызов make_submission.py

# Tests
make check-all

# Deploy
docker compose ps
curl http://localhost:8000/api/v1/predictions/eta\?stop_id\=1\&n\=3

# Docs
cat docs/HACKATHON_CHECKLIST.md
ls slides/  # или docs/pitch/
```

## Out of Scope (за 48ч не делаем)

- ❌ Новые ML фичи (T-169 anomaly)
- ❌ Refactoring кода
- ❌ Тюнинг гиперпараметров
- ❌ Расширение функционала сверх MVP
- ❌ KudaGo events integration (T-164)

## Status

`ready` → `in-progress` → `done`
