"""T-218: load_tier — пороги маппинга load_pct → tier.

Single source of truth = apps/backend/app/load_tier.py.
Пороги должны совпадать с apps/frontend/src/lib/loadTier.ts.
"""

from __future__ import annotations

from app.load_tier import compute_load_tier


def test_load_tier_green_under_70() -> None:
    assert compute_load_tier(0.0) == "green"
    assert compute_load_tier(50.0) == "green"
    assert compute_load_tier(69.9) == "green"


def test_load_tier_yellow_70_to_90() -> None:
    assert compute_load_tier(70.0) == "yellow"
    assert compute_load_tier(80.0) == "yellow"
    assert compute_load_tier(89.9) == "yellow"


def test_load_tier_red_90_to_110() -> None:
    assert compute_load_tier(90.0) == "red"
    assert compute_load_tier(100.0) == "red"
    assert compute_load_tier(109.9) == "red"


def test_load_tier_darkred_110_and_above() -> None:
    assert compute_load_tier(110.0) == "darkred"
    assert compute_load_tier(150.0) == "darkred"
    assert compute_load_tier(999.0) == "darkred"


def test_load_tier_boundaries_inclusive() -> None:
    """Граничные значения (70, 90, 110) включены в ВЕРХНИЙ бакет (так совпадает с TypeScript)."""
    assert compute_load_tier(70.0) == "yellow"
    assert compute_load_tier(90.0) == "red"
    assert compute_load_tier(110.0) == "darkred"
