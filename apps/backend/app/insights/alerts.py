"""Dispatch-time overload alerts (T-131).

Pure stdlib + a thin re-use of `app.schemas.eta.ETAPrediction`. No I/O.
Imported by both the FastAPI endpoint (`app.api.alerts`) and unit tests.

Severity thresholds mirror AC p.3 of T-131:

    75 <= load_pct <  90   -> "info"      (monitor)
    90 <= load_pct < 110   -> "warning"   (crowded)
    load_pct        >=110 -> "critical"  (overloaded)

`time_to_overload_min`: the `eta_min` of the *specific* tram that the
alert refers to (i.e. minutes until this tram departs the stop). Each
alert carries its own time-to-overload, which is what the dispatcher UI
renders on each card ("route 7 -> overload in 8 min").
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.schemas.eta import ETAPrediction

SEVERITY_INFO_MIN: float = 75.0
SEVERITY_WARNING_MIN: float = 90.0
SEVERITY_CRITICAL_MIN: float = 110.0
ALERT_LOAD_THRESHOLD: float = SEVERITY_INFO_MIN

# Re-export of MAX_LOAD_PCT from app.forecast.load -- duplicated here so
# `app.schemas.alerts` doesn't need to import the forecast module just
# for a constant. Anchored to the canonical value (T-128, capacity_model.md).
MAX_LOAD_PCT: float = 150.0

DEFAULT_WINDOW_MIN: int = 30
# F-097: лимит поднят с 120 до 1440 (1 день), чтобы покрывать кнопку "1 день" в
# HorizonToggle (T-200) без 422. Для бо́льших горизонтов (месяц/год) используется
# параметр `horizon=day|month|year` в /api/v1/insights/alerts, а не window_min.
MAX_WINDOW_MIN: int = 1440  # 1 day
HORIZONS: tuple[str, ...] = ("day", "month", "year")
DEFAULT_HORIZON: str = "day"

# Количество ближайших ETA на маршрут в зависимости от горизонта.
# Ограничено, чтобы не упереться в перфоманс-стену для года.
HORIZON_ETA_COUNT: Mapping[str, int] = {
    "day": 5,  # ~каждые 5-10 мин в пик
    "month": 30,  # 30 ближайших трамваев = аппроксимация месячного горизонта
    "year": 60,  # 60 ближайших = ~сутки в пик, более широкий обзор
}

_SEVERITY_RANK: Mapping[str, int] = {
    "critical": 0,
    "warning": 1,
    "info": 2,
}

Severity = str  # "info" | "warning" | "critical"


@dataclass(frozen=True, slots=True)
class OverloadAlert:
    """One actionable alert for the dispatcher UI."""

    stop_id: int
    route_id: int
    route_name: str
    predicted_load_pct: float
    time_to_overload_min: int
    severity: Severity


def classify_load(load_pct: float) -> str:
    """Map ``load_pct`` to one of "info"/"warning"/"critical"."""
    if load_pct < SEVERITY_INFO_MIN:
        return "info"  # caller filters via ALERT_LOAD_THRESHOLD
    if load_pct < SEVERITY_WARNING_MIN:
        return "info"
    if load_pct < SEVERITY_CRITICAL_MIN:
        return "warning"
    return "critical"


def _route_meta(route_meta: Mapping[int, Any], route_id: int) -> tuple[int, str]:
    """Look up (route_id, route_name) from user-supplied ``route_meta``."""
    meta = route_meta.get(route_id)
    if meta is None:
        return route_id, str(route_id)
    name = getattr(meta, "name", None)
    if name is None and isinstance(meta, Mapping):
        name = meta.get("name")
    return route_id, str(name) if name is not None else str(route_id)


def find_overload_alerts(
    eta_by_route: Mapping[int, Iterable[ETAPrediction]],
    route_meta: Mapping[int, Any],
    *,
    window_min: int,
    stop_routes_in_scope: Iterable[int],
) -> list[OverloadAlert]:
    """Compute overload alerts for the dispatcher.

    Sort order: severity rank ascending (critical -> warning -> info),
    then ``time_to_overload_min`` ascending within each severity.
    """
    scope = set(stop_routes_in_scope)
    if not scope:
        return []

    alerts: list[OverloadAlert] = []
    for stop_id in scope:
        etas = list(eta_by_route.get(stop_id, ()))
        for eta in etas:
            if eta.eta_min > window_min:
                continue
            if eta.predicted_load_pct < ALERT_LOAD_THRESHOLD:
                continue
            rid, rname = _route_meta(route_meta, eta.route_id)
            alerts.append(
                OverloadAlert(
                    stop_id=stop_id,
                    route_id=rid,
                    route_name=rname,
                    predicted_load_pct=eta.predicted_load_pct,
                    time_to_overload_min=eta.eta_min,
                    severity=classify_load(eta.predicted_load_pct),
                )
            )

    alerts.sort(
        key=lambda a: (
            _SEVERITY_RANK.get(a.severity, 99),
            a.time_to_overload_min,
            a.stop_id,
            a.route_id,
        )
    )
    return alerts


__all__ = [
    "ALERT_LOAD_THRESHOLD",
    "DEFAULT_HORIZON",
    "DEFAULT_WINDOW_MIN",
    "HORIZONS",
    "HORIZON_ETA_COUNT",
    "MAX_LOAD_PCT",
    "MAX_WINDOW_MIN",
    "SEVERITY_CRITICAL_MIN",
    "SEVERITY_INFO_MIN",
    "SEVERITY_WARNING_MIN",
    "OverloadAlert",
    "classify_load",
    "find_overload_alerts",
]
