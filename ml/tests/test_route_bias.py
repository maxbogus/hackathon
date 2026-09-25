"""Tests for per-route bias calibration (T-147, F-020).

Bias correction: pred_calibrated = pred * exp(median(log1p(actual) - log1p(pred)))
per route. Цель — исправить систематическое завышение/занижение baseline по маршрутам
(см. F-020: route 25, 50, 7, 28 слабее других).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from transit_ai.calibration.route_bias import (
    apply_route_bias,
    compute_route_bias,
)


def test_compute_route_bias_perfect_predictions_returns_zero() -> None:
    """Если actual == pred для всех строк, bias = 0 для всех routes."""
    df = pd.DataFrame(
        {
            "actual": [100.0, 200.0, 50.0, 150.0],
            "pred": [100.0, 200.0, 50.0, 150.0],
            "route_id": [1, 1, 7, 7],
        }
    )
    biases = compute_route_bias(df["actual"], df["pred"], df["route_id"])
    assert biases == {1: 0.0, 7: 0.0}


def test_compute_route_bias_underprediction_positive_log_bias() -> None:
    """Если pred занижает actual в 2 раза, log_bias = log1p(actual) - log1p(pred) > 0."""
    df = pd.DataFrame(
        {
            "actual": [200.0, 100.0],  # higher
            "pred": [100.0, 50.0],  # занижаем в 2 раза
            "route_id": [1, 1],
        }
    )
    biases = compute_route_bias(df["actual"], df["pred"], df["route_id"])
    # bias[1] = median(log1p(200) - log1p(100), log1p(100) - log1p(50))
    # log1p(200)=5.30, log1p(100)=4.61 → 0.69
    # log1p(100)=4.61, log1p(50)=3.93  → 0.68
    # median ≈ 0.685
    assert biases[1] > 0.5, biases
    assert biases[1] < 0.8, biases


def test_apply_route_bias_unknown_route_uses_zero_bias() -> None:
    """Route без записи в biases → bias=0, коррекция = 1.0 (no change)."""
    preds = np.array([10.0, 20.0, 30.0])
    route_ids = np.array([1, 99, 7])  # 99 не в biases
    biases = {1: 0.5, 7: -0.3}
    out = apply_route_bias(preds, route_ids, biases)
    # route=1: 10 * exp(0.5) ≈ 16.49
    assert np.isclose(out[0], 10 * np.exp(0.5), rtol=1e-3)
    # route=99: 20 * exp(0) = 20 (no change)
    assert out[1] == 20.0
    # route=7: 30 * exp(-0.3) ≈ 22.22
    assert np.isclose(out[2], 30 * np.exp(-0.3), rtol=1e-3)


def test_apply_route_bias_clip_to_zero() -> None:
    """Очень отрицательный bias не должен уводить prediction в отрицательные."""
    preds = np.array([1.0])
    route_ids = np.array([1])
    biases = {1: -100.0}  # exp(-100) ≈ 0
    out = apply_route_bias(preds, route_ids, biases)
    assert out[0] >= 0.0


def test_compute_route_bias_raises_on_empty() -> None:
    """Пустой train DataFrame → ValueError."""
    df = pd.DataFrame(columns=["actual", "pred", "route_id"])
    with pytest.raises(ValueError, match="empty"):
        compute_route_bias(df["actual"], df["pred"], df["route_id"])


def test_apply_route_bias_does_not_mutate_input() -> None:
    """apply_route_bias не должен мутировать входной массив predictions."""
    preds = np.array([10.0, 20.0])
    preds_copy = preds.copy()
    route_ids = np.array([1, 1])
    biases = {1: 0.5}
    _ = apply_route_bias(preds, route_ids, biases)
    np.testing.assert_array_equal(preds, preds_copy)


def test_route_bias_end_to_end_improves_wape() -> None:
    """Sanity-check: bias correction на завышенном baseline → уменьшает WAPE.

    Симулируем: actual=200, pred=100 (занижаем в 2 раза) для route 1.
    Без bias: WAPE = Σ|100|/Σ200 = 0.5 → score = 0.5.
    С bias (≈ exp(0.69) = 2.0): pred_calibrated = 100 * 2.0 = 200 → WAPE = 0.
    """
    train = pd.DataFrame(
        {
            "actual": [200.0, 150.0, 250.0],
            "pred": [100.0, 75.0, 125.0],
            "route_id": [1, 1, 1],
        }
    )
    biases = compute_route_bias(train["actual"], train["pred"], train["route_id"])
    test_actual = np.array([200.0, 150.0, 250.0])
    test_pred = np.array([100.0, 75.0, 125.0])
    test_route_ids = np.array([1, 1, 1])

    # Без bias: WAPE = 0.5
    denom = test_actual.sum()
    wape_before = float(np.abs(test_actual - test_pred).sum() / denom)

    # С bias
    calibrated = apply_route_bias(test_pred, test_route_ids, biases)
    wape_after = float(np.abs(test_actual - calibrated).sum() / denom)

    assert wape_before > 0.45  # baseline плохой
    assert wape_after < wape_before  # calibration улучшила
    assert wape_after < 0.1  # почти идеально
