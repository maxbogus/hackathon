"""Per-tram capacity lookup + load_pct computation + colour scale (T-128).

This module owns the *domain constant* `TRAM_CAPACITY` (dict route_id -> int).
It is intentionally separate from `app.config.Settings`:

- `app.config.Settings` is pydantic-settings: runtime knobs read from ENV
  (database_url, redis_url, cors_origins, artifacts_dir).
- `TRAM_CAPACITY` is a *business constant*: capacity of a tram model doesn't
  change between dev/test/prod deployments. It is documented in
  `docs/hackathon/capacity_model.md` and may be replaced by a DB lookup once
  the Department of Transport exposes per-route composition data.

Public surface:
    DEFAULT_TRAM_CAPACITY:  fallback when route_id has no override (150 pax).
    TRAM_CAPACITY:          immutable mapping {route_id: capacity_pax}.
    MAX_LOAD_PCT:           upper clamp for load_pct (150% = critical overload).
    capacity_for(route_id): lookup helper, returns int.
    compute_load_pct(count, route_id): float in [0, MAX_LOAD_PCT].
    load_color(load_pct):  "green" | "yellow" | "red" | "darkred".

This module has no I/O, no FastAPI, no Pydantic — pure stdlib so it can be
imported from anywhere (including `app.data.transit`, which wires it into
the ETA endpoint).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Literal

# --- Constants --------------------------------------------------------------

# Default capacity: среднее для «Витязь-Москва» (3-секционный, ~150 пассажиров
# seated+standing). Используется когда route_id не перечислен в TRAM_CAPACITY.
DEFAULT_TRAM_CAPACITY: Final[int] = 150

# Per-route override. Т1 и Т2 — диаметры с длинными составами (~250 pax).
# Источник: docs/hackathon/capacity_model.md.
TRAM_CAPACITY: Final[MappingProxyType[int, int]] = MappingProxyType(
    {
        1: 250,  # Т1 (diameter, long consist)
        2: 250,  # Т2 (diameter, long consist)
    }
)

# Upper clamp for load_pct. Values above 150% are unrealistic and would only
# confuse the dispatcher UI; clamp instead of returning NaN / infinity.
# 150% = critical overload (vs. 100% = full, vs. 110% = uncomfortable).
MAX_LOAD_PCT: Final[float] = 150.0

# Colour scale thresholds — kept here so the scale is a single source of truth.
_GREEN_MAX: Final[float] = 70.0  # load_pct < 70  → green   (comfortable)
_YELLOW_MAX: Final[float] = 90.0  # 70..90         → yellow  (acceptable)
_RED_MAX: Final[float] = 110.0  # 90..110        → red     (crowded)
# >110                               → darkred (overloaded)

LoadColor = Literal["green", "yellow", "red", "darkred"]


# --- Helpers ----------------------------------------------------------------


def capacity_for(route_id: int) -> int:
    """Return passenger capacity for `route_id` (default if unknown)."""
    return TRAM_CAPACITY.get(route_id, DEFAULT_TRAM_CAPACITY)


def _clip(value: float, lo: float, hi: float) -> float:
    """Saturating clamp — replaces numpy.clip to avoid pulling numpy here."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def compute_load_pct(predicted_count: float, route_id: int) -> float:
    """Convert predicted passenger count to a percentage of tram capacity.

    Returns a float in [0, MAX_LOAD_PCT]. Negative counts (model bug guard)
    are clamped to 0.0; overloads beyond 150% are clamped to MAX_LOAD_PCT.

    Args:
        predicted_count: hourly passenger forecast for this stop (≥ 0 typically).
        route_id: numeric route id (e.g. 7 for route "7", 1 for "Т1").

    Returns:
        Load percentage, e.g. 87.5 means the tram is expected to be 87.5% full.
    """
    capacity = capacity_for(route_id)
    pct = predicted_count / capacity * 100.0
    return float(_clip(pct, 0.0, MAX_LOAD_PCT))


def load_color(load_pct: float) -> LoadColor:
    """Map a load_pct value to a four-step colour scale.

    Boundaries are inclusive on the upper edge (>=70 → yellow, etc.) so that
    exactly-70 is "warning" not "comfortable". Out-of-range values are
    clamped to the nearest bucket.

    Buckets:
        <  70%  → "green"    (comfortable)
        <  90%  → "yellow"   (acceptable, but monitor)
        < 110%  → "red"      (crowded)
        ≥ 110%  → "darkred"  (overloaded)
    """
    if load_pct < _GREEN_MAX:
        return "green"
    if load_pct < _YELLOW_MAX:
        return "yellow"
    if load_pct < _RED_MAX:
        return "red"
    return "darkred"


__all__ = [
    "DEFAULT_TRAM_CAPACITY",
    "MAX_LOAD_PCT",
    "TRAM_CAPACITY",
    "capacity_for",
    "compute_load_pct",
    "load_color",
]
