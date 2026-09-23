"""Static transit metadata + ETA computation (T-127).

Why static and not from DB?
- MVP scope: dataset is synthetic and small. No `stops`/`routes` tables
  exist yet (T-015 alembic init covers only the schema, no real fixture).
- Real data integration lives in T-026 (RealSource adapter) — when
  organizers' parquet lands, this module reads from there.

Hardcoded layout intentionally mirrors `apps/frontend/src/mocks/stops.json`
so the demo for the jury looks identical whether `VITE_USE_MOCK=1` or
`VITE_USE_MOCK=0` (only the data source changes).

Per-route tram capacity lives in `app.forecast.load` (T-128). This module
re-exports `DEFAULT_TRAM_CAPACITY` for backward-compat with T-127 tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final

from app.forecast.load import (
    DEFAULT_TRAM_CAPACITY as _DEFAULT_TRAM_CAPACITY,
)
from app.forecast.load import (
    MAX_LOAD_PCT,
    capacity_for,
)
from app.schemas.eta import ETAPrediction

if TYPE_CHECKING:
    from transit_ai.models.base import PredictionPoint, Predictor


# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RouteRef:
    """One route that calls at a stop."""

    id: int
    name: str


# Mirrors apps/frontend/src/mocks/stops.json — kept in lock-step.
# id → ordered list of routes that call there.
STOP_ROUTES: Final[dict[int, tuple[RouteRef, ...]]] = {
    1: (RouteRef(7, "7"), RouteRef(9, "9"), RouteRef(10, "А")),
    2: (RouteRef(3, "3"), RouteRef(39, "39"), RouteRef(10, "А")),
    3: (RouteRef(7, "7"), RouteRef(9, "9")),
    4: (RouteRef(27, "27"), RouteRef(29, "29")),
}

# Backward-compat re-export — the canonical home is `app.forecast.load`
# (T-128). Kept here because T-127 tests import `DEFAULT_TRAM_CAPACITY`
# from this module. Will be removed once those tests are updated to import
# from `app.forecast.load` directly.
DEFAULT_TRAM_CAPACITY: Final[int] = _DEFAULT_TRAM_CAPACITY

# Upper bound for the `n` query parameter — the UI only renders up to 5 cards.
MAX_TRAMS_PER_REQUEST: Final[int] = 5

# Time horizon for the bucket scan (60 min — one full peak commute).
HORIZON_MINUTES: Final[int] = 60


# ---------------------------------------------------------------------------
# Pure computation
# ---------------------------------------------------------------------------


def clamp_n(n: int, *, lo: int = 1, hi: int = MAX_TRAMS_PER_REQUEST) -> int:
    """Clamp requested N to the supported [lo, hi] range.

    The endpoint itself enforces `n >= 1` via Pydantic, but we keep this
    helper for direct callers (tests, future tooling).
    """
    if n < lo:
        return lo
    if n > hi:
        return hi
    return n


def compute_eta_predictions(
    stop_id: int,
    n: int,
    predictor: Predictor,
    *,
    now: datetime | None = None,
    capacity: int | None = None,
) -> list[ETAPrediction]:
    """Compute next-N upcoming trams at `stop_id` using `predictor`.

    If `capacity` is None (the default), per-route capacity is looked up via
    `app.forecast.load.capacity_for(route_id)` for each tram — T1/T2 get
    250 (diameter), everything else gets 150 (Витязь-Москва).

    Algorithm:
        1. Predict hourly ridership over [now, now + HORIZON_MINUTES].
        2. Split the horizon into `n` equal buckets (60/n minutes each).
        3. For each bucket i:
             - eta_min = (bucket midpoint - now) in minutes (rounded up)
             - load = sum of hourly predictions inside bucket, weighted
               proportionally (linear interpolation)
             - load_pct = clamp(load / capacity * 100, 0, MAX_LOAD_PCT=150)
        4. Assign route_id/route_name from STOP_ROUTES (cycle if fewer
           routes than requested).

    Returns an empty list if the stop has no route metadata (UI renders
    this as "no data" via recommend()).

    Why a function and not a class?
    - The endpoint stays thin; logic is independently testable.
    - No side effects: same inputs → same outputs, easy to snapshot.
    """
    routes = STOP_ROUTES.get(stop_id)
    if not routes:
        return []

    n = clamp_n(n)
    if now is None:
        # Avoid importing datetime.now at module scope so tests can
        # override `now` deterministically. UTC for stable serialization
        # across timezones (Pydantic emits ISO 8601 with offset).
        now = datetime.now(tz=UTC)

    horizon_end = now + timedelta(minutes=HORIZON_MINUTES)
    hourly_points = predictor.predict(stop_id, now, horizon_end)

    # Convert hourly PredictionPoint list into per-bucket load sums.
    # Each hourly point covers exactly 60 minutes (BaselineMean contract).
    # We slice the [0, HORIZON_MINUTES] timeline into N equal buckets and
    # distribute each hour's load across buckets proportionally to overlap.
    bucket_loads: list[float] = _split_load_into_buckets(hourly_points, now, n)

    bucket_width_min = HORIZON_MINUTES // n
    result: list[ETAPrediction] = []
    for i, load in enumerate(bucket_loads):
        bucket_mid = now + timedelta(
            minutes=bucket_width_min * i + bucket_width_min // 2
        )
        eta_min = max(0, int((bucket_mid - now).total_seconds() // 60))
        route = routes[i % len(routes)]
        # Per-route capacity (T-128): diameter routes Т1/Т2 get 250, all others
        # get DEFAULT_TRAM_CAPACITY (150). Explicit kwarg wins for tests/legacy
        # callers; otherwise we look up by route_id from STOP_ROUTES.
        route_capacity = capacity if capacity is not None else capacity_for(route.id)
        load_pct = _clamp(load / route_capacity * 100.0, 0.0, MAX_LOAD_PCT)
        # Round to 1 decimal — load_pct floats get noisy with many decimals.
        load_pct = round(load_pct, 1)

        result.append(
            ETAPrediction(
                route_id=route.id,
                route_name=route.name,
                eta_min=eta_min,
                predicted_load_pct=load_pct,
                model_id=predictor.model_id,
            )
        )

    return result


def _split_load_into_buckets(
    hourly_points: list[PredictionPoint],
    now: datetime,
    n: int,
) -> list[float]:
    """Distribute hourly predictions across N equal-width buckets.

    For each hourly point [period_start, period_end), its load (the `value`
    field) is a sum across the full hour. We assume uniform distribution
    within the hour and credit each bucket a share proportional to the
    overlap minutes.
    """
    if n <= 0:
        return []
    bucket_width_min = HORIZON_MINUTES // n
    buckets = [0.0] * n

    for point in hourly_points:
        # Clip the hourly interval to [now, now + HORIZON_MINUTES].
        clip_start = max(point.period_start, now)
        clip_end = min(point.period_end, now + timedelta(minutes=HORIZON_MINUTES))
        if clip_start >= clip_end:
            continue

        # Distribute this hour's load uniformly per minute.
        minutes_in_clip = (clip_end - clip_start).total_seconds() / 60.0
        load_per_min = point.value / 60.0

        # Walk buckets, accumulate the per-minute load for each bucket
        # overlapping with the clipped interval.
        cur = clip_start
        while cur < clip_end:
            bucket_idx = int((cur - now).total_seconds() // 60 // bucket_width_min)
            if bucket_idx < 0:
                bucket_idx = 0
            elif bucket_idx >= n:
                break
            # Bucket end boundary in absolute time.
            bucket_end_abs = now + timedelta(
                minutes=(bucket_idx + 1) * bucket_width_min
            )
            minutes_in_bucket = min(
                (bucket_end_abs - cur).total_seconds() / 60.0, minutes_in_clip
            )
            buckets[bucket_idx] += load_per_min * minutes_in_bucket
            cur = bucket_end_abs
            minutes_in_clip -= minutes_in_bucket
            if minutes_in_clip <= 0:
                break

    return buckets


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


__all__ = [
    "DEFAULT_TRAM_CAPACITY",
    "HORIZON_MINUTES",
    "MAX_TRAMS_PER_REQUEST",
    "STOP_ROUTES",
    "RouteRef",
    "clamp_n",
    "compute_eta_predictions",
]
