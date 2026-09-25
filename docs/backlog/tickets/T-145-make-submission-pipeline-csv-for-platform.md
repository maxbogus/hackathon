---
id: T-145
phase: 2
title: submission pipeline — ml/scripts/make_submission.py → submission.csv (14640 строк)
priority: P0
effort: 3
unit: hours
rice:
  R: 10
  I: 3.0
  C: 0.9
  score: 9.00
depends_on: [T-143, T-144]
blocks: []
tags: [ml, submission, hackathon, platform, p0]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-145: submission pipeline → submission.csv

## Context

Платформа хакатона принимает CSV: `route;date;hour;prediction` (F-015).
Submission покрывает **полную сетку 10 routes × 61 day × 24 hour = 14 640 строк**
(data/real/README.md секция 6).

**Submission горизонт:** 2025-11-01 → 2025-12-31 (61 день).

**Дедлайн:** 27.09.2025 23:59 МСК. Лимит: 36 попыток всего / 24 успешных в день.

Задача: `make submission` → генерит `predictions/submission_<model_id>_<date>.csv`
с полной сеткой и прогнозами. WAPE-score на holdout (сен–окт 2025) — proxy.

## Acceptance Criteria

- [ ] `ml/scripts/make_submission.py`:
  - `--start-date` (default 2025-11-01)
  - `--end-date` (default 2025-12-31)
  - `--model-id` (default: из active.json или None → route_baseline)
  - `--output` (default: predictions/submission_<model_id>_<date>.csv)
  - `--coef-weather / --coef-event / --coef-season` (default 1.0, T-147)
- [ ] Создаёт полную сетку: 10 routes × 61 day × 24 hours = 14 640 строк
- [ ] Использует `RouteBaselineMean` (новый, обученный на train 2025-01..08)
- [ ] Оценка WAPE-score на test (сен–окт 2025) перед записью submission
- [ ] Unit-тест `ml/tests/test_make_submission.py`:
  - Output shape (14640)
  - Columns route;date;hour;prediction
  - Date range (2025-11-01..2025-12-31)
  - Все routes присутствуют
  - prediction ≥ 0
  - WAPE-score reported
- [ ] `make submission` работает end-to-end

## Technical Notes

```python
"""Generate submission.csv для платформы хакатона (T-145)."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from transit_ai.data.real import RealSource
from transit_ai.data.base import DateRange
from transit_ai.models.route_baseline import RouteBaselineMean
from transit_ai.reports.metrics import compute_metrics

ROUTES = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2025-11-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--model-id", default="route_baseline_v1")
    parser.add_argument("--output", default=None)
    parser.add_argument("--coef-weather", type=float, default=1.0)
    parser.add_argument("--coef-event", type=float, default=1.0)
    parser.add_argument("--coef-season", type=float, default=1.0)
    args = parser.parse_args()

    start = datetime.strptime(args.start_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")
    days = (end - start).days + 1

    # 1. Train model on train (jan-aug 2025)
    src = RealSource()
    train_df = src.load_ridership(DateRange(datetime(2025, 1, 1), datetime(2025, 8, 31)))
    model = RouteBaselineMean()
    model.fit(train_df)

    # 2. Evaluate on test (sep-oct 2025)
    test_df = src.load_ridership(DateRange(datetime(2025, 9, 1), datetime(2025, 10, 31)))
    test_pred = model.predict_batch(test_df)
    metrics = compute_metrics(test_df["boardings"].values, test_pred)
    print(f"Holdout WAPE-score (сен-окт): {metrics['wape_score']:.4f}")
    print(f"  MAE={metrics['mae']:.1f}, WAPE={metrics['wape']:.4f}")

    # 3. Build full grid for submission
    records = []
    for d in range(days):
        cur = start + timedelta(days=d)
        for route in ROUTES:
            for hour in range(24):
                pred = model.predict_route(route=route, date=cur, hour=hour)
                # Apply coefficients (T-147)
                pred *= args.coef_weather * args.coef_event * args.coef_season
                records.append({
                    "route": route,
                    "date": cur.strftime("%Y-%m-%d"),
                    "hour": hour,
                    "prediction": max(0.0, round(pred, 2)),
                })

    df = pd.DataFrame(records)
    print(f"Submission shape: {df.shape}")

    # 4. Save
    output = Path(args.output) if args.output else (
        Path("predictions") / f"submission_{args.model_id}_{datetime.now():%Y%m%d_%H%M}.csv"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, sep=";", index=False)
    print(f"Saved to: {output}")
    return 0
```

## Verification

```bash
make submission
# → predictions/submission_route_baseline_v1_20250925_HHMM.csv
# → 14640 rows, columns route;date;hour;prediction

wc -l predictions/submission_*.csv
# 14641 (14640 + header)

# Validate format
head -3 predictions/submission_*.csv
# route;date;hour;prediction
# 1;2025-11-01;0;0.0
# 1;2025-11-01;1;0.0
```

## Beneficiary Impact

**Команда (⭐⭐⭐)** — submission pipeline = заливка на платформу = баллы.
**Жюри (⭐⭐⭐)** — единый формат, воспроизводимость (git_commit, train_data_hash).

RICE: 9.00 — максимальный приоритет, финальный шаг перед сабмитом.
