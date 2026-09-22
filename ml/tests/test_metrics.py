"""Tests for transit_ai.reports.metrics (RMSLE, MAE, MAPE, compute_metrics).

Это общий модуль метрик: перенесён из ml/transit_ai/benchmark/runner.py.
Используется в evaluate.py (T-035), benchmark (T-038), plots (T-037).
"""
from __future__ import annotations

import numpy as np
import pytest

from transit_ai.reports.metrics import compute_metrics, mae, mape, rmsle


def test_rmsle_perfect_prediction_returns_zero() -> None:
    """pred == true → RMSLE = 0."""
    y = np.array([1.0, 5.0, 10.0, 100.0])
    assert rmsle(y, y) == 0.0


def test_rmsle_clips_negative_inputs() -> None:
    """Negative y_true/y_pred clipped to 0 (log1p undefined for x < -1)."""
    y_true = np.array([-5.0, 0.0, 10.0])
    y_pred = np.array([0.0, 5.0, 20.0])
    score = rmsle(y_true, y_pred)
    assert isinstance(score, float)
    assert score >= 0.0
    clipped_true = np.maximum(y_true, 0)
    clipped_pred = np.maximum(y_pred, 0)
    expected = float(
        np.sqrt(np.mean((np.log1p(clipped_pred) - np.log1p(clipped_true)) ** 2))
    )
    assert score == pytest.approx(expected)


def test_mae_symmetry() -> None:
    """MAE is symmetric and matches manual computation."""
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([2.0, 3.0, 4.0])
    assert mae(y_true, y_pred) == 1.0
    assert mae(y_pred, y_true) == 1.0


def test_mape_excludes_zero_actuals() -> None:
    """MAPE skips y_true == 0 rows (no division by zero)."""
    y_true = np.array([0.0, 100.0, 50.0])
    y_pred = np.array([10.0, 110.0, 55.0])
    # Only [100, 50] count: |110-100|/100 + |55-50|/50 = 0.1 + 0.1 → mean = 0.1 → 10%
    assert mape(y_true, y_pred) == pytest.approx(10.0)


def test_mape_returns_zero_when_all_actuals_zero() -> None:
    """MAPE on all-zero y_true → 0.0 (guard against empty mask)."""
    y_true = np.array([0.0, 0.0, 0.0])
    y_pred = np.array([1.0, 2.0, 3.0])
    assert mape(y_true, y_pred) == 0.0


def test_compute_metrics_returns_all_three() -> None:
    """compute_metrics возвращает dict с rmsle/mae/mape (>=0)."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    y_pred = np.array([12.0, 22.0, 28.0, 42.0, 48.0])
    metrics = compute_metrics(y_true, y_pred)
    assert isinstance(metrics, dict)
    assert set(metrics.keys()) == {"rmsle", "mae", "mape"}
    for v in metrics.values():
        assert isinstance(v, float)
        assert v >= 0.0


def test_compute_metrics_handles_empty_arrays() -> None:
    """compute_metrics on empty arrays → zeros (no crash)."""
    empty = np.array([])
    metrics = compute_metrics(empty, empty)
    assert metrics == {"rmsle": 0.0, "mae": 0.0, "mape": 0.0}
