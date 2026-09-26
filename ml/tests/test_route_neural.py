"""Tests for RouteNeuralPredictor (T-177-NEURAL-CONFIG).

Unified sequence encoder: gru | lstm | mamba (по шаблону contest neural_models.py).

Контракт:
- RouteNeuralConfig: (kind, hidden, layers, seq_len, lr, epochs, route_emb_dim, use_calendar)
- RouteNeuralPredictor: fit/predict_batch/save/load с теми же сигнатурами что GRURoutePredictor
- backward compat: GRURoutePredictor = RouteNeuralPredictor с kind="gru"
- Mamba (SSM) — pure PyTorch, no external deps (R1: BSD-compatible)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from transit_ai.models.route_neural import (
    RouteNeuralConfig,
    RouteNeuralPredictor,
)


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


def test_route_neural_config_defaults() -> None:
    """RouteNeuralConfig имеет ожидаемые defaults."""
    cfg = RouteNeuralConfig()
    assert cfg.kind in ("gru", "lstm", "mamba")
    assert cfg.hidden == 64
    assert cfg.layers == 2
    assert cfg.seq_len == 336
    assert cfg.lr == 3e-4
    assert cfg.epochs == 20
    assert cfg.route_emb_dim == 32
    assert cfg.use_calendar is True


def test_route_neural_gru_predict_shape() -> None:
    """GRU через RouteNeuralPredictor возвращает правильный shape."""
    model = RouteNeuralPredictor(
        config=RouteNeuralConfig(kind="gru", seq_len=48, hidden=32, layers=1, epochs=2),
        model_id="rneural_gru_test",
    )
    history = _make_minimal_history(n_days=7, n_routes=2)
    model.fit(history)

    future = pd.DataFrame(
        [
            {"timestamp": datetime(2025, 6, 8, 0, tzinfo=UTC), "route_id": 1, "hour": 0},
            {"timestamp": datetime(2025, 6, 8, 1, tzinfo=UTC), "route_id": 1, "hour": 1},
            {"timestamp": datetime(2025, 6, 8, 0, tzinfo=UTC), "route_id": 2, "hour": 0},
        ]
    )
    preds = model.predict_batch(future)
    assert len(preds) == 3
    assert isinstance(preds, np.ndarray)
    assert (preds >= 0).all()


def test_route_neural_lstm_predict_shape() -> None:
    """LSTM forward shape совпадает с GRU."""
    model = RouteNeuralPredictor(
        config=RouteNeuralConfig(kind="lstm", seq_len=48, hidden=32, layers=1, epochs=2),
        model_id="rneural_lstm_test",
    )
    history = _make_minimal_history(n_days=7, n_routes=2)
    model.fit(history)

    future = pd.DataFrame(
        [{"timestamp": datetime(2025, 6, 8, 0, tzinfo=UTC), "route_id": 1, "hour": 0}]
    )
    preds = model.predict_batch(future)
    assert len(preds) == 1
    assert (preds >= 0).all()


def test_route_neural_mamba_predict_shape() -> None:
    """Mamba (SSM) forward shape совпадает с GRU/LSTM."""
    model = RouteNeuralPredictor(
        config=RouteNeuralConfig(kind="mamba", seq_len=48, hidden=32, layers=1, epochs=2),
        model_id="rneural_mamba_test",
    )
    history = _make_minimal_history(n_days=7, n_routes=2)
    model.fit(history)

    future = pd.DataFrame(
        [{"timestamp": datetime(2025, 6, 8, 0, tzinfo=UTC), "route_id": 1, "hour": 0}]
    )
    preds = model.predict_batch(future)
    assert len(preds) == 1
    assert (preds >= 0).all()


def test_route_neural_unknown_kind_raises() -> None:
    """Неизвестный kind → ValueError при попытке использовать."""
    with pytest.raises(ValueError, match="[Uu]nsupported kind"):
        # RouteNeuralConfig accepts any string, but SequenceModel raises on build
        from transit_ai.models.route_neural import SequenceModel
        SequenceModel(
            kind="transformer",  # type: ignore[arg-type]
            input_dim=64,
            hidden=64,
            layers=1,
            n_routes=10,
        )


def test_route_neural_config_persistence(tmp_path) -> None:
    """Config сохраняется в state_dict и восстанавливается при load()."""
    cfg = RouteNeuralConfig(kind="lstm", hidden=64, layers=2, seq_len=168, epochs=5)
    model = RouteNeuralPredictor(config=cfg, model_id="save_lstm")
    history = _make_minimal_history(n_days=10, n_routes=2)
    model.fit(history)

    p = tmp_path / "rneural.pkl"
    model.save(str(p))
    loaded = RouteNeuralPredictor.load(str(p))

    assert loaded.config.kind == "lstm"
    assert loaded.config.hidden == 64
    assert loaded.config.layers == 2
    assert loaded.config.seq_len == 168
    assert loaded.fitted_ is True
