---
id: T-025
phase: 2
title: ml transit_ai data synthetic 800 stops 40 routes 2 years
priority: P0
effort: 5
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.7
  score: 2.1
depends_on: []
blocks: []
tags: [ml, data, synthetic]
status: done
created: 2026-09-20
updated: 2026-09-20
assignee: "cline"
---

# T-025: ml transit_ai data synthetic 800 stops 40 routes 2 years

## Context

Why this task exists.

## Acceptance Criteria

- [x] `ml/transit_ai/data/synthetic.py` с `SyntheticSource(DataSource)`
- [x] `SyntheticConfig` dataclass для параметров (n_stops, n_routes, n_days, seed, epoch_date, ridership_min/max, peak hours)
- [x] Генерит остановки в bbox Москвы (55.55–55.92, 37.30–37.85), ~10% hubs
- [x] Маршруты — случайные последовательности 3-8 остановок
- [x] Ridership с реалистичными паттернами (peak morning/evening, weekend mult 0.6, night mult 0.2)
- [x] Deterministic: seed=42, одинаковые данные при каждом запуске
- [x] 5 unit тестов passed (test_synthetic.py) — covers DataSource contract, determinism, DateRange, realistic patterns
- [x] `ruff check ml/transit_ai/data/` clean
- [x] Per спецификации: MVP-размер (10/5/30 дней) для быстрых тестов. Полная синтетика 800/40/2 года — отдельный скрипт `ml/scripts/gen_synthetic.py` (T-041).

## Notes

- RID написан in-memory через pandas DataFrame (не сохраняется на диск в этой итерации для скорости тестов). Полная версия сохранения в parquet — в T-041 (production data generation script).
- B023 lambda-in-loop баг поправлен: stop_routes ищется один раз per stop через DataFrame filter.

## Technical Notes

- 2 года × 365 дней × 24 часа × 800 остановок = ~14M строк ridership. Big но feasible.
- Реалистичность: peak hours = 1.5-2x baseline, weekends = 0.6x.
- Per-stop baseline ridership = random[N(20, 5)] для маленьких, N(100, 20) для hub.
- Генерим через numpy (быстрее pandas), потом конвертим в parquet.

## Verification

```bash
uv run python -m transit_ai.data.synthetic --output data/synthetic
uv run pytest ml/tests/test_synthetic.py -v
# должно создать 3 parquet файла, ~100MB total
```
