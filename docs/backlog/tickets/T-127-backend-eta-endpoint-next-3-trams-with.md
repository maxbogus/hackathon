---
id: T-127
phase: 1
title: backend endpoint /api/v1/predictions/eta — прогноз ETA + загрузки для следующих 3 рейсов
priority: P0
effort: 3
unit: hours
rice:
  R: 8
  I: 3.0
  C: 0.8
  score: 6.4
depends_on: [T-019, T-033, T-098]
blocks: [T-128, T-129]
tags: [backend, api, eta, passenger, beneficiary]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-127: backend endpoint `/api/v1/predictions/eta` — прогноз ETA + загрузки для следующих 3 рейсов

## Context

Главная боль пассажира: «Когда приедет трамвай и будет ли место?» Прямо решает user story:
«Как пассажир, я хочу видеть прогноз прибытия и загрузки следующих N рейсов на моей остановке,
чтобы решить — садиться или ждать».

Endpoint возвращает массив ближайших рейсов (ETA + загрузка). Используется в T-129 (режим
«Пассажир» в Streamlit) и T-130 (бизнес-логика рекомендации).

## Acceptance Criteria

- [ ] Endpoint `GET /api/v1/predictions/eta?stop_id=X&n=3` добавлен в `apps/backend/app/api/predictions.py`
- [ ] Response schema `ETAResponse` в Pydantic:
  - `stop_id: int`
  - `trams: list[ETAPrediction]` где `ETAPrediction`:
    - `route_id: int`
    - `route_name: str`
    - `eta_min: int` (0-60)
    - `predicted_load_pct: float` (0-100)
    - `model_id: str`
- [ ] Алгоритм: берёт текущее время, активную модель из registry, предсказывает
  пассажиропоток на следующие 60 минут с шагом 5-15 мин (3 точки)
- [ ] ETA вычисляется как `t_arrival - t_now`, где `t_arrival` — следующий пик нагрузки
  на этом stop_id (или фиксированный интервал если данных мало)
- [ ] Если активная модель не поддерживает per-stop per-5min — fallback на hourly forecast
- [ ] CORS headers настроены для Streamlit (разные порты)
- [ ] Smoke test: `curl http://localhost:8000/api/v1/predictions/eta?stop_id=1&n=3`
  возвращает валидный JSON

## Technical Notes

Архитектура: использует существующий `Predictor.predict(stop_id, period_start, period_end)`
из registry. Для ETA нужна агрегация hourly → per-5min (или новый тип predict).

Pydantic schemas в `apps/backend/app/schemas/predictions.py` (уже есть T-017).

Алгоритм ETA (упрощённый):
```python
def compute_eta_predictions(stop_id, n, model):
    now = datetime.now()
    horizon_end = now + timedelta(minutes=60)
    preds = model.predict(stop_id, now, horizon_end)  # hourly points
    # Агрегируем по 3 бакетам (next, next+20, next+40)
    # Вычисляем load_pct = (predicted_count / capacity) * 100
    # ETA_min = (bucket_start - now) / 60
    return ETAResponse(...)
```

Capacity можно захардкодить: «Витязь-Москва» = 150-200 пассажиров, "Львёнок-Москва" = 100.

## Verification

```bash
make up  # backend на :8000
curl "http://localhost:8000/api/v1/predictions/eta?stop_id=1&n=3" | jq
# Ожидаем JSON с 3 элементами в trams[]
```

## Beneficiary Impact

**Пассажиры (⭐⭐⭐⭐⭐)** — прямо решает главную боль.
**Департамент** — endpoint готов к интеграции в Яндекс.Транспорт / mos.ru API.

RICE: 6.4 — топ-13. Делается в Фазе 1.
