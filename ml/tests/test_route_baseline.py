"""Tests for RouteBaselineMean — route-level baseline (T-145)."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from transit_ai.models.route_baseline import RouteBaselineMean


def _make_ridership() -> pd.DataFrame:
    """Создаёт тестовые данные: 10 дней × 2 маршрута × 24 часа = 480 строк."""
    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    rows = []
    for d in dates:
        for route in (1, 7):
            for h in range(24):
                # Простой паттерн: 100 boardings в 8:00, 200 в 18:00, 0 ночью
                if h == 8:
                    b = 100 + route
                elif h == 18:
                    b = 200 + route
                elif h < 5 or h > 22:
                    b = 0
                else:
                    b = 50 + route
                rows.append({
                    "timestamp": d + pd.Timedelta(hours=h),
                    "route_id": route,
                    "date": d,
                    "hour": h,
                    "boardings": float(b),
                })
    return pd.DataFrame(rows)


def test_fit_builds_table_per_route_hour_weekday() -> None:
    model = RouteBaselineMean()
    df = _make_ridership()
    model.fit(df)
    assert model.fitted_
    assert len(model.table_) > 0
    # По 2 маршрута × 24 часа × 7 weekday = 336 buckets (max)
    assert len(model.table_) == 2 * 24 * 7


def test_predict_returns_single_value() -> None:
    model = RouteBaselineMean()
    model.fit(_make_ridership())
    pred = model.predict_route(route=1, date=datetime(2025, 11, 1), hour=8)
    # Среднее за все (date, weekday, hour=8) для route=1
    assert isinstance(pred, float)
    assert pred > 0


def test_predict_batch_returns_array() -> None:
    model = RouteBaselineMean()
    train = _make_ridership()
    model.fit(train)
    test = train.head(100).copy()
    preds = model.predict_batch(test)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == len(test)
    assert (preds >= 0).all()


def test_predict_route_no_data_returns_zero() -> None:
    """Новый route (нет в train) → 0 или global fallback."""
    model = RouteBaselineMean()
    model.fit(_make_ridership())
    pred = model.predict_route(route=999, date=datetime(2025, 11, 1), hour=8)
    # Если global_table_ есть (по hour=8) → mean ≈ 100 (см. _make_ridership)
    # Если пусто → 0.0
    assert isinstance(pred, float)
    assert pred >= 0


def test_wape_score_better_than_constant_baseline() -> None:
    """RouteBaselineMean должен быть лучше baseline (constant = mean всех boardings)."""
    df = _make_ridership()
    model = RouteBaselineMean()
    model.fit(df)
    preds = model.predict_batch(df)

    # WAPE-score для model
    from transit_ai.reports.metrics import compute_metrics

    model_metrics = compute_metrics(df["boardings"].values, preds)
    # WAPE-score для constant baseline (predict mean of all)
    const_pred = np.full(len(df), df["boardings"].mean())
    const_metrics = compute_metrics(df["boardings"].values, const_pred)

    assert model_metrics["wape_score"] > const_metrics["wape_score"]


def test_cold_start_uses_global_fallback() -> None:
    """Для (route=999, hour=8) → среднее всех (weekday, hour=8)."""
    df = _make_ridership()
    model = RouteBaselineMean()
    model.fit(df)
    pred_known = model.predict_route(route=1, date=datetime(2025, 11, 1), hour=8)
    pred_unknown = model.predict_route(route=999, date=datetime(2025, 11, 1), hour=8)
    # Оба должны быть похожи (fallback на global mean)
    assert abs(pred_known - pred_unknown) < pred_known * 0.5  # в пределах 50%
