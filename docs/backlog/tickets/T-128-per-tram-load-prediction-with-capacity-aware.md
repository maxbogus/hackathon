---
id: T-128
phase: 1
title: прогноз загрузки рейса (load_pct) с учётом capacity трамвая
priority: P0
effort: 2
unit: hours
rice:
  R: 7
  I: 3.0
  C: 0.8
  score: 8.4
depends_on: [T-127]
blocks: [T-129, T-130]
tags: [backend, ml, load-prediction, beneficiary]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-128: прогноз загрузки рейса (load_pct) с учётом capacity трамвая

## Context

Боль пассажира: «Будет ли место в трамвае?» Без перевода `passenger_count` → `load_pct`
(процент заполнения) число бесполезно для пассажира. 50 человек в трамвае — это «много» или
«мало»? Зависит от capacity.

Решает user story: «Как пассажир, я хочу видеть % заполненности трамвая, чтобы понять —
стоит ли в него садиться или подождать следующий».

## Acceptance Criteria

- [ ] Константа `TRAM_CAPACITY` в `apps/backend/app/config.py`: dict `route_id → capacity`
- [ ] Default capacity: 150 пассажиров (среднее для «Витязь-Москва»)
- [ ] Capacity override для Т1, Т2 (диаметры, длинные составы): 250
- [ ] Функция `compute_load_pct(predicted_count: float, route_id: int) -> float` в `apps/backend/app/forecast/load.py`
- [ ] Clipping: load_pct ∈ [0, 150] (>100% = перегруз, до 150% = критично)
- [ ] Цветовая шкала: green <70%, yellow 70-90%, red 90-110%, dark_red >110%
- [ ] Документировано в `docs/hackathon/capacity_model.md` (откуда цифры, как валидировать)
- [ ] Unit-тест: `test_compute_load_pct.py` (5+ кейсов: empty, half, full, overload, edge cases)

## Technical Notes

Capacity lookup (захардкожен, не из API):

```python
TRAM_CAPACITY = {
    # Диаметры (длинные составы)
    1: 250,    # Т1
    2: 250,    # Т2
    # Стандартные маршруты
    # (по умолчанию 150)
}

def compute_load_pct(predicted_count: float, route_id: int) -> float:
    capacity = TRAM_CAPACITY.get(route_id, 150)
    return float(np.clip(predicted_count / capacity * 100, 0, 150))
```

Данные о реальной вместимости:
- «Витязь-Москва» (3-секционный): ~150-200 пасс
- «Львёнок-Москва» (1-секционный, автономный ход): ~80-100 пасс
- Т1/Т2 диаметры: длинные составы, ~250 пасс

Если есть доступ к API Департамента — уточнить реальные значения по маршрутам.

## Verification

```bash
uv run pytest apps/backend/tests/test_compute_load_pct.py -v
# 5+ тестов должны быть зелёными

# Smoke test в API
curl "http://localhost:8000/api/v1/predictions/eta?stop_id=1&n=3" | jq '.trams[0].predicted_load_pct'
# Должно вернуть float 0-150
```

## Beneficiary Impact

**Пассажиры (⭐⭐⭐⭐⭐)** — информация в понятных единицах (% заполнения).
**Департамент** — capacity-aware метрики готовы к внедрению в инфраструктуру.

RICE: 8.4 — топ-8 приоритет. Делается в Фазе 1.
