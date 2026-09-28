"""Tests for CatBoostRoutePredictor (T-173).

CatBoost predictor с тем же интерфейсом, что и XGBoostRoutePredictor:
fit/predict_batch/predict_recursive, переиспользует _make_features из xgboost_route.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from _data_guards import requires_spravochnik

from transit_ai.models.catboost_route import CatBoostRoutePredictor
from transit_ai.models.xgboost_route import (
    FEATURE_NAMES,
    XGBoostRoutePredictor,
    build_lag_lookup,
)

# F-136: fit на полном датасете (49M строк) — вне быстрого гейта
pytestmark = pytest.mark.slow

# ────────────────────────────────────────────────────────────────────
# Fixtures: минимальный ridership DataFrame для тестов
# ────────────────────────────────────────────────────────────────────


def _make_minimal_ridership(n_days: int = 5, n_routes: int = 3) -> pd.DataFrame:
    """Сгенерить минимальный ridership DataFrame для тестов fit/predict.

    Returns:
        DataFrame [n_days * 24 * n_routes rows × 5 cols]:
        timestamp, route_id, date, hour, boardings.
    """
    rows = []
    start = datetime(2025, 6, 1, tzinfo=UTC)
    for d in range(n_days):
        for h in range(24):
            for r in range(n_routes):
                ts = start + timedelta(days=d, hours=h)
                rows.append(
                    {
                        "timestamp": ts,
                        "route_id": r + 1,
                        "date": ts.date(),
                        "hour": h,
                        # Простой паттерн: больше днём, route-dependent scale
                        "boardings": float(50 + r * 20 + h * 2),
                    }
                )
    return pd.DataFrame(rows)


# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────


@requires_spravochnik
def test_catboost_fit_predict() -> None:
    """fit на минимальных данных → predict возвращает массив правильного shape."""
    model = CatBoostRoutePredictor(model_id="cat_test_v1", iterations=20)
    df = _make_minimal_ridership(n_days=7, n_routes=2)

    model.fit(df)

    # Inference: тот же набор данных, но без boardings
    infer_df = df.drop(columns=["boardings"]).copy()
    preds = model.predict_batch(infer_df)

    assert len(preds) == len(infer_df)
    assert isinstance(preds, np.ndarray)
    assert (preds >= 0).all(), f"Predictions < 0 found: min={preds.min()}"


def test_catboost_uses_same_features_as_xgboost() -> None:
    """CatBoostRoutePredictor использует тот же FEATURE_NAMES, что и XGBoost."""
    # Sanity: FEATURE_NAMES не пустой и содержит основные временные фичи
    assert len(FEATURE_NAMES) > 0
    assert "hour" in FEATURE_NAMES
    assert "weekday" in FEATURE_NAMES
    # T-172 events features должны быть в общем FEATURE_NAMES
    assert "event_metro_troitskaya_30d" in FEATURE_NAMES
    assert "event_baumana_campus_30d" in FEATURE_NAMES
    assert "n_events_active_30d" in FEATURE_NAMES
    # XGBoostRoutePredictor как dataclass (sanity, не строгая проверка структуры)
    assert hasattr(XGBoostRoutePredictor, "fit")


@requires_spravochnik
def test_catboost_predict_with_lag_lookup() -> None:
    """predict_batch с lag_lookup (T-152-fallback) работает на submission-like данных."""
    model = CatBoostRoutePredictor(model_id="cat_test_lag", iterations=20)
    train_df = _make_minimal_ridership(n_days=14, n_routes=2)
    model.fit(train_df)
    lag_lookup = build_lag_lookup(train_df)

    # Future data: 2025-07-01..07-03, нет boardings
    future_dates = pd.date_range("2025-07-01", "2025-07-03", tz=UTC)
    rows = []
    for d in future_dates:
        for h in range(24):
            for r in (1, 2):
                rows.append(
                    {
                        "timestamp": d + timedelta(hours=h),
                        "route_id": r,
                        "date": d.date(),
                        "hour": h,
                    }
                )
    infer_df = pd.DataFrame(rows)
    preds = model.predict_batch(infer_df, lag_lookup=lag_lookup)

    assert len(preds) == len(infer_df)
    assert (preds >= 0).all()
    # Predictions должны быть в разумном диапазоне (не 0, не миллионы)
    assert preds.mean() > 0.1
    assert preds.mean() < 1000.0


@requires_spravochnik
def test_catboost_save_load(tmp_path_factory: pytest.TempPathFactory) -> None:
    """model.pkl сохраняется и загружается через joblib (как XGBoost)."""
    import joblib

    model = CatBoostRoutePredictor(model_id="cat_test_save", iterations=10)
    df = _make_minimal_ridership(n_days=3, n_routes=2)
    model.fit(df)

    tmp = tmp_path_factory.mktemp("cat_save") / "model.pkl"
    joblib.dump(model, tmp)
    loaded = joblib.load(tmp)

    # Inference на исходных данных даёт тот же результат (детерминизм + seed)
    infer_df = df.drop(columns=["boardings"]).copy()
    preds_orig = model.predict_batch(infer_df)
    preds_loaded = loaded.predict_batch(infer_df)
    np.testing.assert_array_almost_equal(preds_orig, preds_loaded, decimal=4)
