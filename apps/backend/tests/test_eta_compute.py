"""Unit tests for `app.data.transit.compute_eta_predictions` (T-127).

Pure-function tests — no FastAPI, no TestClient. Verifies that the
algorithm itself behaves correctly given a controlled predictor.

Coverage:
- Bucket distribution of hourly load
- Capacity scaling (load_pct arithmetic)
- Clamping logic
- Empty result for unknown stops
- Cycle-on-routes when n > len(routes)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from app.data.transit import (
    DEFAULT_TRAM_CAPACITY,
    MAX_TRAMS_PER_REQUEST,
    STOP_ROUTES,
    clamp_n,
    compute_eta_predictions,
)


@dataclass
class _FakePoint:
    """Minimal PredictionPoint stand-in — only the fields we touch."""

    period_start: datetime
    period_end: datetime
    value: float


class _FakePredictor:
    """Predictor that returns a fixed hourly value for any query.

    Used to make the algorithm deterministic without fitting a real
    BaselineMean.
    """

    model_id = "fake_v1"
    kind = "fake"

    def __init__(self, hourly_value: float = 60.0) -> None:
        self.hourly_value = hourly_value

    def predict(self, stop_id: int, period_start: datetime, period_end: datetime):
        from datetime import timedelta

        # Return one hour-long point per hour in range, each with the same value.
        from transit_ai.models.base import PredictionPoint

        points: list[PredictionPoint] = []
        cur = period_start
        while cur < period_end:
            points.append(
                PredictionPoint(
                    period_start=cur,
                    period_end=cur + timedelta(hours=1),
                    value=self.hourly_value,
                    lower=self.hourly_value * 0.8,
                    upper=self.hourly_value * 1.2,
                    stop_id=stop_id,
                    model_id=self.model_id,
                )
            )
            cur += timedelta(hours=1)
        return points


# ---- clamp_n ----


def test_clamp_n_passes_through_in_range() -> None:
    assert clamp_n(3) == 3


def test_clamp_n_low_clamps_to_1() -> None:
    assert clamp_n(0) == 1
    assert clamp_n(-5) == 1


def test_clamp_n_high_clamps_to_max() -> None:
    assert clamp_n(MAX_TRAMS_PER_REQUEST + 1) == MAX_TRAMS_PER_REQUEST
    assert clamp_n(100) == MAX_TRAMS_PER_REQUEST


# ---- compute_eta_predictions ----


def test_compute_returns_n_results_for_known_stop() -> None:
    predictor = _FakePredictor(hourly_value=60.0)
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(stop_id=1, n=3, predictor=predictor, now=now)
    assert len(result) == 3


def test_compute_returns_empty_for_unknown_stop() -> None:
    predictor = _FakePredictor()
    result = compute_eta_predictions(stop_id=9999, n=3, predictor=predictor)
    assert result == []


def test_compute_load_pct_uses_capacity() -> None:
    """With hourly_value=60 and capacity=150, 1 full hour = 60/150*100 = 40%.

    With 60-min horizon and n=1, the single bucket gets the entire 60 min of
    load = 60 (since we credit load_per_min * 60 min in the bucket).
    """
    predictor = _FakePredictor(hourly_value=60.0)
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(
        stop_id=1, n=1, predictor=predictor, now=now, capacity=150
    )
    assert len(result) == 1
    # Bucket spans 60 minutes of horizon with n=1 → receives all hourly load.
    assert result[0].predicted_load_pct == pytest.approx(40.0, abs=0.1)


def test_compute_load_pct_clamped_to_100() -> None:
    """An overloaded hour (300 passengers, capacity=150) → 100%, not 200%."""
    predictor = _FakePredictor(hourly_value=300.0)
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(
        stop_id=1, n=1, predictor=predictor, now=now, capacity=150
    )
    assert result[0].predicted_load_pct == 100.0


def test_compute_load_pct_clamped_to_0_for_zero_load() -> None:
    """A zero-ridership hour → 0%, not negative."""
    predictor = _FakePredictor(hourly_value=0.0)
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(stop_id=1, n=3, predictor=predictor, now=now)
    for tram in result:
        assert tram.predicted_load_pct == 0.0


def test_compute_eta_min_increases_with_bucket_index() -> None:
    predictor = _FakePredictor(hourly_value=60.0)
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(stop_id=1, n=3, predictor=predictor, now=now)
    etas = [t.eta_min for t in result]
    assert etas == sorted(etas)
    assert etas[0] < etas[1] < etas[2]


def test_compute_cycles_routes_when_n_exceeds_routes() -> None:
    """Stop 3 only has 2 routes → with n=5, routes cycle."""
    predictor = _FakePredictor()
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(stop_id=3, n=5, predictor=predictor, now=now)
    assert len(result) == 5
    # First 2 trams must be stop 3's actual routes (7, 9), then cycles back.
    assert [r.route_id for r in result] == [7, 9, 7, 9, 7]


def test_compute_uses_default_capacity() -> None:
    """If capacity is not passed, DEFAULT_TRAM_CAPACITY (150) is used."""
    predictor = _FakePredictor(hourly_value=DEFAULT_TRAM_CAPACITY)
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(stop_id=1, n=1, predictor=predictor, now=now)
    # 150 passengers / 150 capacity * 100 = 100%
    assert result[0].predicted_load_pct == 100.0


def test_compute_sets_model_id_from_predictor() -> None:
    predictor = _FakePredictor()
    now = datetime(2026, 9, 23, 10, 0, 0)
    result = compute_eta_predictions(stop_id=1, n=3, predictor=predictor, now=now)
    assert all(t.model_id == "fake_v1" for t in result)


def test_stop_routes_matches_mock_frontend() -> None:
    """STOP_ROUTES must stay in sync with apps/frontend/src/mocks/stops.json."""
    assert set(STOP_ROUTES.keys()) == {1, 2, 3, 4}
    assert [r.id for r in STOP_ROUTES[1]] == [7, 9, 10]
    assert [r.name for r in STOP_ROUTES[1]] == ["7", "9", "А"]
    assert [r.id for r in STOP_ROUTES[4]] == [27, 29]
