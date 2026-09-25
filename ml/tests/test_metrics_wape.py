"""Tests for WAPE/WAPE-score metrics (T-144)."""
from __future__ import annotations

import numpy as np
import pytest

from transit_ai.reports.metrics import (
    compute_metrics,
    wape,
    wape_score,
)


def test_wape_perfect_prediction() -> None:
    y = np.array([10, 20, 30, 40])
    assert wape(y, y) == 0.0
    assert wape_score(y, y) == 1.0


def test_wape_50_percent_error() -> None:
    """Если ошибка = 50% от истинного → WAPE = 0.5, score = 0.5."""
    y = np.array([100.0, 100.0])
    p = np.array([50.0, 150.0])
    # |100-50| + |100-150| = 50 + 50 = 100; Σy = 200; WAPE = 0.5
    assert wape(y, p) == pytest.approx(0.5)
    assert wape_score(y, p) == pytest.approx(0.5)


def test_wape_baseline_hackathon() -> None:
    """Hackathon baseline ≈ 0.48 (WAPE ≤ 0.52). Score = 0.48."""
    y = np.array([100.0] * 100)
    p = y * 0.5  # на 50% занижаем
    assert wape(y, p) == pytest.approx(0.5)
    assert wape_score(y, p) == pytest.approx(0.5)


def test_wape_all_zeros() -> None:
    """Σy = 0 → WAPE = inf, score = 0. Не падать."""
    y = np.array([0.0, 0.0, 0.0])
    p = np.array([0.0, 0.0, 0.0])
    assert wape_score(y, p) == 0.0  # graceful (через max(0, 1−inf)=0)


def test_wape_negative_predictions_clipped() -> None:
    """Negative predictions clipped to 0 (как и RMSLE)."""
    y = np.array([10.0, 20.0])
    p = np.array([-5.0, 15.0])  # -5 → 0; |10-0|=10, |20-15|=5; Σ=15; Σy=30; WAPE=0.5
    assert wape(y, p) == pytest.approx(0.5)


def test_wape_empty_arrays() -> None:
    """Пустые массивы → WAPE=0, score=1 (no crash)."""
    y = np.array([])
    p = np.array([])
    assert wape(y, p) == 0.0
    assert wape_score(y, p) == 1.0


def test_compute_metrics_returns_all_5_keys() -> None:
    y = np.array([10.0, 20.0, 30.0])
    p = np.array([12.0, 18.0, 33.0])
    metrics = compute_metrics(y, p)
    assert set(metrics.keys()) == {"rmsle", "mae", "mape", "wape", "wape_score"}
    assert 0.0 <= metrics["wape_score"] <= 1.0
    assert metrics["wape"] >= 0.0


def test_wape_score_negative_clamped_to_zero() -> None:
    """Если WAPE > 1 (overprediction в 2x), score = 0 (НЕ отрицательный)."""
    y = np.array([100.0])
    p = np.array([300.0])  # overprediction 200%; WAPE = 200/100 = 2.0; score = max(0, 1−2) = 0
    assert wape_score(y, p) == 0.0


def test_compute_metrics_with_empty() -> None:
    """Пустые массивы не падают."""
    metrics = compute_metrics(np.array([]), np.array([]))
    assert metrics == {"rmsle": 0.0, "mae": 0.0, "mape": 0.0, "wape": 0.0, "wape_score": 0.0}
