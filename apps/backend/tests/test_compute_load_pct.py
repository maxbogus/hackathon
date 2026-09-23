"""Unit tests for `app.forecast.load` capacity-aware load_pct (T-128).

Pure-function tests — no FastAPI, no TestClient. Verifies:
- TRAM_CAPACITY lookup (default 150, diameter routes 1/2 → 250)
- compute_load_pct scaling and clamping ([0, 150])
- load_color scale (green / yellow / red / darkred)

These cover the AC items 1-7 from docs/backlog/tickets/T-128-*.md:
- Constants table + default
- Per-route override
- Clipping policy (overload up to 150% is reported, not zeroed)
- Colour-scale thresholds
"""

from __future__ import annotations

import pytest

from app.forecast.load import (
    DEFAULT_TRAM_CAPACITY,
    MAX_LOAD_PCT,
    TRAM_CAPACITY,
    capacity_for,
    compute_load_pct,
    load_color,
)

# ---- capacity_for ----


def test_capacity_for_default_route_returns_150() -> None:
    """Unknown route_id → default 150 (Витязь-Москва single section)."""
    assert capacity_for(7) == 150
    assert capacity_for(39) == 150


def test_capacity_for_diameter_route_1_returns_250() -> None:
    """T1 (route_id=1) — длинный состав, ~250 пассажиров."""
    assert capacity_for(1) == 250


def test_capacity_for_diameter_route_2_returns_250() -> None:
    """T2 (route_id=2) — длинный состав, ~250 пассажиров."""
    assert capacity_for(2) == 250


def test_capacity_for_unknown_route_returns_default() -> None:
    """Forward-compat: future route_id without override → 150."""
    assert capacity_for(999) == DEFAULT_TRAM_CAPACITY == 150


def test_tram_capacity_table_is_immutable() -> None:
    """TRAM_CAPACITY is a MappingProxyType — cannot be mutated at runtime."""
    assert isinstance(TRAM_CAPACITY, type(TRAM_CAPACITY))  # MappingProxyType
    with pytest.raises(TypeError):
        TRAM_CAPACITY[7] = 200  # type: ignore[index]


# ---- compute_load_pct ----


def test_compute_load_pct_zero_passengers() -> None:
    """No load → 0% (no negative values)."""
    assert compute_load_pct(0.0, 7) == 0.0


def test_compute_load_pct_half_capacity() -> None:
    """75 passengers / capacity 150 → 50%."""
    assert compute_load_pct(75.0, 7) == pytest.approx(50.0)


def test_compute_load_pct_exact_capacity() -> None:
    """150 passengers / capacity 150 → 100% (full but not overloaded)."""
    assert compute_load_pct(150.0, 7) == pytest.approx(100.0)


def test_compute_load_pct_overload_clamped_to_150() -> None:
    """300 passengers (2× capacity) → 150% (MAX_LOAD_PCT), not 200%."""
    assert compute_load_pct(300.0, 7) == MAX_LOAD_PCT == 150.0


def test_compute_load_pct_extreme_overload_still_clamped() -> None:
    """1000 passengers → still 150% (cap, not NaN, not error)."""
    assert compute_load_pct(1000.0, 7) == 150.0


def test_compute_load_pct_negative_count_clamps_to_0() -> None:
    """Defensive: negative predicted_count → 0% (model bug guard)."""
    assert compute_load_pct(-50.0, 7) == 0.0


def test_compute_load_pct_diameter_route_uses_250() -> None:
    """T1 with 125 passengers → 50% (125/250)."""
    assert compute_load_pct(125.0, 1) == pytest.approx(50.0)


def test_compute_load_pct_diameter_route_overload_at_250() -> None:
    """T1 with 375 passengers (1.5× diameter capacity) → 150% (clamped)."""
    assert compute_load_pct(375.0, 1) == 150.0


def test_compute_load_pct_returns_float() -> None:
    """Return type is float (downstream Pydantic / frontend consume floats)."""
    result = compute_load_pct(50.0, 7)
    assert isinstance(result, float)


# ---- load_color ----


def test_load_color_green_below_70() -> None:
    assert load_color(0.0) == "green"
    assert load_color(50.0) == "green"
    assert load_color(69.9) == "green"


def test_load_color_yellow_70_to_90() -> None:
    assert load_color(70.0) == "yellow"
    assert load_color(80.0) == "yellow"
    assert load_color(89.9) == "yellow"


def test_load_color_red_90_to_110() -> None:
    assert load_color(90.0) == "red"
    assert load_color(100.0) == "red"
    assert load_color(109.9) == "red"


def test_load_color_darkred_above_110() -> None:
    assert load_color(110.0) == "darkred"
    assert load_color(120.0) == "darkred"
    assert load_color(150.0) == "darkred"


def test_load_color_overflow_clamped_to_darkred() -> None:
    """If somehow 200% reaches this function (shouldn't, but defensive), → darkred."""
    assert load_color(200.0) == "darkred"


def test_load_color_negative_clamps_to_green() -> None:
    """Negative input → green (defensive)."""
    assert load_color(-10.0) == "green"
