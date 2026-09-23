"""Unit tests for `app.insights.alerts.find_overload_alerts` (T-131).

Pure-function tests — no FastAPI, no DB. Verifies:
- Severity classification per AC thresholds (info/warning/critical)
- Sub-75% load_pct produces NO alert (filtered out)
- `time_to_overload_min` = eta_min of the first ≥90% prediction (expert variant)
- Stable ordering: severity-desc, then time_to_overload_min asc
- Empty input → empty output
- Alerts beyond the `window_min` horizon are excluded

Severity scale (mirrors AC p.3):

    75 <= load_pct <  90   → "info"
    90 <= load_pct < 110   → "warning"
    load_pct        >= 110 → "critical"

The implementation lives in `apps/backend/app/insights/alerts.py` (T-131
GREEN phase). RED phase: this file imports it and asserts behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.insights.alerts import (
    SEVERITY_CRITICAL_MIN,
    SEVERITY_INFO_MIN,
    SEVERITY_WARNING_MIN,
    OverloadAlert,
    find_overload_alerts,
)
from app.schemas.eta import ETAPrediction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Route:
    """Minimal stand-in for route metadata passed to find_overload_alerts."""

    id: int
    name: str


_STOP_1: Final[int] = 1
_STOP_2: Final[int] = 2


def _eta(
    route_id: int, route_name: str, eta_min: int, load_pct: float
) -> ETAPrediction:
    """Build an ETAPrediction fixture with predictable values."""
    return ETAPrediction(
        route_id=route_id,
        route_name=route_name,
        eta_min=eta_min,
        predicted_load_pct=load_pct,
        model_id="baseline_v1",
    )


def _route(rid: int, name: str = "R") -> _Route:
    return _Route(id=rid, name=name)


# ---------------------------------------------------------------------------
# Severity boundaries
# ---------------------------------------------------------------------------


def test_severity_info_at_75_lower_edge() -> None:
    """load_pct == 75.0 -> 'info' (lower edge of info band is inclusive)."""
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=75.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert len(alerts) == 1
    assert alerts[0].severity == "info"


def test_severity_warning_at_90_lower_edge() -> None:
    """load_pct == 90.0 -> 'warning'."""
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=90.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert len(alerts) == 1
    assert alerts[0].severity == "warning"


def test_severity_critical_at_110() -> None:
    """load_pct == 110.0 -> 'critical' (>=110 inclusive)."""
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=110.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"


def test_severity_critical_at_150_top_of_clamp() -> None:
    """load_pct == 150.0 (MAX_LOAD_PCT) -> 'critical'."""
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=150.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"


# ---------------------------------------------------------------------------
# Filtering -- sub-threshold load produces NO alert
# ---------------------------------------------------------------------------


def test_below_info_threshold_returns_no_alert() -> None:
    """load_pct == 70.0 -> no alert (below info band)."""
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=70.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert alerts == []


def test_empty_eta_list_returns_no_alerts() -> None:
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: []},
        route_meta={},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert alerts == []


def test_no_stops_in_scope_returns_no_alerts() -> None:
    alerts = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=120.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope=set(),
    )
    assert alerts == []


# ---------------------------------------------------------------------------
# time_to_overload_min semantics -- expert variant
# ---------------------------------------------------------------------------


def test_time_to_overload_uses_first_eta_at_or_above_90pct() -> None:
    """First >=90% prediction in the list drives time_to_overload_min."""
    alerts = find_overload_alerts(
        eta_by_route={
            _STOP_1: [
                _eta(7, "7", eta_min=8, load_pct=92.0),  # first >=90 -> 8 min
                _eta(9, "9", eta_min=20, load_pct=85.0),  # info, secondary
            ]
        },
        route_meta={7: _route(7), 9: _route(9)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert len(alerts) == 2
    # After severity ordering: warning (92%) precedes info (85%)
    warning = next(a for a in alerts if a.severity == "warning")
    info = next(a for a in alerts if a.severity == "info")
    assert warning.time_to_overload_min == 8
    assert warning.stop_id == _STOP_1
    assert warning.route_id == 7
    assert warning.predicted_load_pct == 92.0
    assert info.route_id == 9
    assert info.time_to_overload_min == 20


def test_window_filters_eta_beyond_horizon() -> None:
    """ETA > window_min is excluded from alerts."""
    alerts = find_overload_alerts(
        eta_by_route={
            _STOP_1: [
                _eta(7, "7", eta_min=15, load_pct=120.0),  # in window (<=30)
                _eta(9, "9", eta_min=45, load_pct=120.0),  # out of window -> drop
            ]
        },
        route_meta={7: _route(7), 9: _route(9)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    assert len(alerts) == 1
    assert alerts[0].route_id == 7


def test_multiple_stops_each_emits_its_own_alert() -> None:
    alerts = find_overload_alerts(
        eta_by_route={
            _STOP_1: [_eta(7, "7", eta_min=5, load_pct=92.0)],
            _STOP_2: [_eta(3, "3", eta_min=10, load_pct=125.0)],
        },
        route_meta={7: _route(7), 3: _route(3)},
        window_min=30,
        stop_routes_in_scope={_STOP_1, _STOP_2},
    )
    by_stop = {a.stop_id: a for a in alerts}
    assert set(by_stop) == {_STOP_1, _STOP_2}
    assert by_stop[_STOP_1].severity == "warning"
    assert by_stop[_STOP_2].severity == "critical"


# ---------------------------------------------------------------------------
# Output structure & ordering
# ---------------------------------------------------------------------------


def test_alert_has_expected_fields() -> None:
    alert = find_overload_alerts(
        eta_by_route={_STOP_1: [_eta(7, "7", eta_min=5, load_pct=92.0)]},
        route_meta={7: _route(7)},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )[0]
    assert isinstance(alert, OverloadAlert)
    assert isinstance(alert.stop_id, int)
    assert isinstance(alert.route_id, int)
    assert isinstance(alert.route_name, str)
    assert isinstance(alert.predicted_load_pct, float)
    assert isinstance(alert.time_to_overload_min, int)
    assert alert.severity in {"info", "warning", "critical"}


def test_global_ordering_is_severity_then_time() -> None:
    """Critical -> warning -> info. Within a severity, by ETA ascending."""
    alerts = find_overload_alerts(
        eta_by_route={
            _STOP_1: [
                _eta(7, "7", eta_min=5, load_pct=85.0),  # info
                _eta(9, "9", eta_min=25, load_pct=95.0),  # warning
                _eta(10, "A", eta_min=15, load_pct=125.0),  # critical
            ]
        },
        route_meta={7: _route(7), 9: _route(9), 10: _route(10, "A")},
        window_min=30,
        stop_routes_in_scope={_STOP_1},
    )
    severities = [a.severity for a in alerts]
    assert severities == ["critical", "warning", "info"]


def test_within_severity_ordered_by_eta_ascending() -> None:
    alerts = find_overload_alerts(
        eta_by_route={
            _STOP_1: [
                _eta(7, "7", eta_min=20, load_pct=120.0),  # critical, late
            ],
            _STOP_2: [
                _eta(3, "3", eta_min=3, load_pct=115.0),  # critical, early
            ],
        },
        route_meta={7: _route(7), 3: _route(3)},
        window_min=30,
        stop_routes_in_scope={_STOP_1, _STOP_2},
    )
    # Both critical -- earliest ETA first
    assert [a.stop_id for a in alerts] == [_STOP_2, _STOP_1]


def test_constants_match_ac_thresholds() -> None:
    """Sanity check on the threshold constants documented in AC p.3."""
    assert SEVERITY_INFO_MIN == 75.0
    assert SEVERITY_WARNING_MIN == 90.0
    assert SEVERITY_CRITICAL_MIN == 110.0


# ---------------------------------------------------------------------------
# Module-level exports
# ---------------------------------------------------------------------------


def test_module_exposes_public_api() -> None:
    """`app.insights.alerts` exposes the canonical surface."""
    import app.insights.alerts as mod

    assert hasattr(mod, "find_overload_alerts")
    assert hasattr(mod, "OverloadAlert")
    assert hasattr(mod, "SEVERITY_INFO_MIN")
    assert hasattr(mod, "SEVERITY_WARNING_MIN")
    assert hasattr(mod, "SEVERITY_CRITICAL_MIN")
    assert hasattr(mod, "ALERT_LOAD_THRESHOLD")


def test_insights_package_importable() -> None:
    """`app.insights` is a real package (not just a namespace)."""
    import app.insights
    import app.insights.alerts  # noqa: F401
