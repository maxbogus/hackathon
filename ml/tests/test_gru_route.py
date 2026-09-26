"""Tests for GRURoutePredictor (T-029, T-175).

Адаптация contest/ecup26-user-value/scripts/experiment_neural_gru.py:
- Embedding(route_id) + Embedding(hour) -> concat -> Linear -> ReLU
- GRU 2x hidden=64 -> attention pooling (learnable query)
- MLP head -> log1p(boardings)
- Sequence length = 168h (7 days)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from transit_ai.models.gru_route import GRURoutePredictor

# Fixtures


def _make_minimal_history(n_days: int = 14, n_routes: int = 3) -> pd.DataFrame:
    """Минимальный ridership для тестов fit/predict."""
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
                        "boardings": float(50 + r * 20 + h * 2),
                    }
                )
    return pd.DataFrame(rows)


# Tests


def test_gru_fit_predict_shape() -> None:
    """fit на малых данных -> predict на future grid возвращает правильный shape."""
    model = GRURoutePredictor(model_id="gru_test_v1", seq_len=48, hidden=32, epochs=2)
    history = _make_minimal_history(n_days=7, n_routes=2)
    model.fit(history)

    future = pd.date_range("2025-06-08", "2025-06-09", tz=UTC)
    rows = []
    for d in future:
        for h in range(24):
            for r in (1, 2):
                rows.append(
                    {"timestamp": d + timedelta(hours=h), "route_id": r, "hour": h}
                )
    future_grid = pd.DataFrame(rows)
    preds = model.predict_batch(future_grid)

    assert len(preds) == len(future_grid)
    assert isinstance(preds, np.ndarray)
    assert (preds >= 0).all()


def test_gru_uses_sequences() -> None:
    """GRU использует sequence длиной seq_len (default 168)."""
    model = GRURoutePredictor(model_id="gru_seq", seq_len=24, hidden=16, epochs=2)
    history = _make_minimal_history(n_days=3, n_routes=2)
    model.fit(history)

    assert model.seq_len_ == 24


def test_gru_predict_with_short_history_uses_mean_fallback() -> None:
    """Если history < seq_len, fallback на mean(boardings) per route."""
    model = GRURoutePredictor(model_id="gru_short", seq_len=168, hidden=16, epochs=1)
    # Только 2 дня истории (меньше seq_len=168)
    history = _make_minimal_history(n_days=2, n_routes=2)
    model.fit(history)

    future = pd.DataFrame(
        [
            {
                "timestamp": datetime(2025, 6, 4, tzinfo=UTC),
                "route_id": 1,
                "hour": 12,
            }
        ]
    )
    preds = model.predict_batch(future)
    assert len(preds) == 1
    assert preds[0] >= 0


def test_gru_save_load_roundtrip(tmp_path) -> None:
    """model сохраняется через save() и загружается через load().

    После load: model_=None, predict работает через fallback_lookup.
    Сравниваем с fallback_predict из исходного экземпляра.
    """
    model = GRURoutePredictor(model_id="gru_save", seq_len=24, hidden=16, epochs=1)
    history = _make_minimal_history(n_days=3, n_routes=2)
    model.fit(history)

    p = tmp_path / "gru.pkl"
    model.save(str(p))
    loaded = GRURoutePredictor.load(str(p))

    assert loaded.fitted_ is True
    assert loaded.route_ids_ == model.route_ids_
    assert loaded.fallback_lookup_ == model.fallback_lookup_

    future = pd.DataFrame(
        [
            {
                "timestamp": datetime(2025, 6, 4, tzinfo=UTC),
                "route_id": 1,
                "hour": 12,
            }
        ]
    )
    # Оба используют fallback (model_=None в loaded, или short history в оригинале)
    p_orig = model._fallback_predict(future)
    p_loaded = loaded.predict_batch(future)
    np.testing.assert_array_almost_equal(p_orig, p_loaded, decimal=4)


def test_gru_handles_empty_raises() -> None:
    """Пустой DataFrame -> ValueError."""
    model = GRURoutePredictor(model_id="gru_empty", seq_len=24, hidden=16, epochs=1)
    with pytest.raises(ValueError, match="empty"):
        model.fit(pd.DataFrame())


def test_gru_requires_columns() -> None:
    """Отсутствие timestamp/route_id/boardings -> ValueError."""
    model = GRURoutePredictor(model_id="gru_cols", seq_len=24, hidden=16, epochs=1)
    bad_df = pd.DataFrame({"foo": [1, 2, 3]})
    with pytest.raises(ValueError, match="Missing columns"):
        model.fit(bad_df)


def test_gru_quick_variant_shape() -> None:
    """T-177-GRU-QUICK: hidden=128, layers=2, seq_len=336 + per-route embedding + calendar features.

    Сигнатура архитектуры (quick variant по шаблону contest):
    - GRUModelV2: route_emb(10→32) + hour_emb(24→8) + calendar_emb(7→4) + weekday_emb(7→4)
                  → Linear(48→hidden) → ReLU → GRU(hidden, layers) → attention pool → MLP(32→1)
    - Target: log1p(boardings)
    """
    model = GRURoutePredictor(
        model_id="gru_quick", seq_len=336, hidden=128, layers=2, epochs=2
    )
    # 14 дней истории = 336h seq_len
    history = _make_minimal_history(n_days=14, n_routes=3)
    model.fit(history)

    # Architecture assertions
    assert model.arch_ == "gru_v2_extended"  # type: ignore[attr-defined]
    assert model.hidden == 128
    assert model.layers == 2
    assert model.seq_len == 336
    # Per-route embedding exists
    assert hasattr(model, "route_emb_dim_")  # type: ignore[attr-defined]
    assert model.route_emb_dim_ == 32  # type: ignore[attr-defined]
