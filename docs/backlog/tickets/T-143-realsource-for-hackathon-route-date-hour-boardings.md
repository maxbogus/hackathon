---
id: T-143
phase: 2
title: RealSource для датасета хакатона (route × date × hour boardings)
priority: P0
effort: 4
unit: hours
rice:
  R: 8
  I: 3.0
  C: 0.9
  score: 5.40
depends_on: []
blocks: [T-144, T-145]
tags: [ml, data, real-source, hackathon, p0]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-143: RealSource для датасета хакатона (route × date × hour boardings)

## Context

Официальное ТЗ (25.09): метрика WAPE-score считается на уровне **(route, date, hour) →
boardings**. Submission.csv = 14640 строк (10 маршрутов × 61 день × 24 часа).
Датасет: `data/real/labels/labels_day_{train,test}.csv` — готовые агрегаты.

Существующий `SyntheticSource` использует `(stop_id, weekday, hour)` — granularity
mismatch. Справочники остановок покрывают только `{1,5,7,11,12}` из 10 маршрутов.
**RealSource НЕ должен зависеть от stop-level данных.**

F-015, D-017: выбран RealSource, читающий labels (не сырые валидации).

## Acceptance Criteria

- [ ] `ml/transit_ai/data/real.py` с классом `RealSource(DataSource)`:
  - `load_stops() -> DataFrame[stop_id, name, lat, lon, route_ids]` (может быть пустой
    или частичный — stop-level не нужен для метрики)
  - `load_routes() -> DataFrame[route_id, name]` (10 маршрутов:
    `{1,5,7,11,12,17,25,26,28,50}`)
  - `load_ridership(date_range) -> DataFrame[timestamp, route_id, hour, date, boardings]`
- [ ] `load_ridership()` читает `data/real/labels/labels_day_*.csv` (агрегаты)
- [ ] Фильтр по `date_range` (inclusive)
- [ ] Конвертация `route` (int из "25 трамвай") → `route_id` (int 25)
- [ ] `validate()` проверяет: 10 уникальных routes, boardings ≥ 0, непрерывная сетка
  hours ∈ {0..23}, нет NaN
- [ ] Работает в standalone режиме без интернета
- [ ] Unit-тест `ml/tests/test_real_source.py`: 5+ кейсов (empty, full, filter,
  bad data, schema check)
- [ ] `ml/scripts/inspect_real.py` CLI: `uv run --directory ml python scripts/inspect_real.py`
  → печатает shape, routes, date range, total boardings

## Technical Notes

```python
"""Real data source для датасета хакатона.

Читает data/real/labels/labels_day_{train,test}.csv (агрегаты по route × date × hour).
Не зависит от stop-level детализации (F-015).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from transit_ai.data.base import DataSource, DateRange


class RealSource(DataSource):
    """Read hackathon route-level ridership data from labels_day_*.csv.

    Returns DataFrame in unified contract:
        [timestamp, route_id, hour, date, boardings]
    where timestamp = pd.Timestamp(date) + pd.Timedelta(hours=hour).
    """

    ROUTES = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)
    DEFAULT_LABELS_DIR = Path("data/real/labels")

    def __init__(self, labels_dir: Path | None = None) -> None:
        self.labels_dir = labels_dir or self.DEFAULT_LABELS_DIR

    def load_stops(self) -> pd.DataFrame:
        # Stop-level не нужен по ТЗ (F-015). Возвращаем пустой DataFrame.
        return pd.DataFrame(columns=["stop_id", "name", "lat", "lon", "route_ids"])

    def load_routes(self) -> pd.DataFrame:
        return pd.DataFrame({
            "route_id": list(self.ROUTES),
            "name": [f"Трамвай {r}" for r in self.ROUTES],
        })

    def load_ridership(self, date_range: DateRange) -> pd.DataFrame:
        train = self._read_labels_file("labels_day_train.csv")
        test = self._read_labels_file("labels_day_test.csv")
        all_df = pd.concat([train, test], ignore_index=True)

        # Filter
        all_df["date"] = pd.to_datetime(all_df["date"])
        mask = (all_df["date"] >= pd.Timestamp(date_range.start.date())) & (
            all_df["date"] <= pd.Timestamp(date_range.end.date())
        )
        filtered = all_df[mask].copy()

        # Contract columns
        filtered["timestamp"] = filtered["date"] + pd.to_timedelta(filtered["hour"], unit="h")
        filtered["route_id"] = filtered["route"].astype(int)
        return filtered[["timestamp", "route_id", "date", "hour", "boardings"]]

    def _read_labels_file(self, filename: str) -> pd.DataFrame:
        path = self.labels_dir / filename
        df = pd.read_csv(path, sep=";", encoding="utf-8")
        self.validate(df)
        return df

    @staticmethod
    def validate(df: pd.DataFrame) -> None:
        """Raise ValueError on schema violations."""
        required = {"route", "date", "hour", "boardings"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        if (df["boardings"] < 0).any():
            raise ValueError(f"Negative boardings: {(df['boardings'] < 0).sum()} rows")
        if not df["hour"].between(0, 23).all():
            raise ValueError(f"Invalid hour values: {df[~df['hour'].between(0, 23)]['hour'].unique()}")
        if df["boardings"].isna().any():
            raise ValueError(f"NaN boardings: {df['boardings'].isna().sum()} rows")
```

## Verification

```bash
uv run pytest ml/tests/test_real_source.py -v
# 5+ тестов зелёные

uv run --directory ml python scripts/inspect_real.py
# RouteBaselineMean data summary

uv run --directory ml python -c "
from transit_ai.data.real import RealSource
from transit_ai.data.base import DateRange
from datetime import datetime
src = RealSource()
df = src.load_ridership(DateRange(datetime(2025,1,1), datetime(2025,1,31)))
print(df.shape, df.columns.tolist())
"
# (310, 5) ['timestamp', 'route_id', 'date', 'hour', 'boardings']
```

## Beneficiary Impact

**Диспетчер (⭐⭐⭐)** — реальные данные → реальные прогнозы → реальные решения.
**Город (⭐⭐⭐)** — метрика WAPE-score на submission.csv определяет 10/39 баллов.

RICE: 5.40 (после F-015: 8×3.0×0.9 / 4h). Делается ПЕРВЫМ в Фазе 2 (блокирует T-144, T-145).
