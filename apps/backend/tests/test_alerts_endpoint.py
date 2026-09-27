"""Integration tests for `GET /api/v1/insights/alerts` (T-131).

Verifies:
- Route is registered under the expected path
- Query params (window_min) are validated
- Response shape matches `OverloadAlertsResponse` Pydantic schema
- Empty alerts case handled
- HTTP status codes per FastAPI conventions (200, 422)
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_alerts_route_returns_200_with_default_window() -> None:
    """Default query (no window_min) returns 200."""
    response = _client().get("/api/v1/insights/alerts")
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert "alerts" in body
    assert "generated_at" in body
    assert "window_min" in body
    assert isinstance(body["alerts"], list)


def test_alerts_route_accepts_window_min_query() -> None:
    response = _client().get("/api/v1/insights/alerts?window_min=15")
    assert response.status_code == 200
    assert response.json()["window_min"] == 15


def test_alerts_route_rejects_negative_window_min() -> None:
    response = _client().get("/api/v1/insights/alerts?window_min=-5")
    assert response.status_code == 422


def test_alerts_route_rejects_overlong_window_min() -> None:
    """window_min > 1440 (1 day) is rejected — F-097: поднято с 120 до 1440.

    F-097: для горизонтов больше 1 дня используется отдельный параметр
    ``horizon=month|year`` (а не window_min в минутах).
    """
    response = _client().get("/api/v1/insights/alerts?window_min=2000")
    assert response.status_code == 422


def test_alerts_route_accepts_horizon_param() -> None:
    """F-097: новый параметр horizon=day|month|year (T-200). Default = 'day'."""
    for horizon in ("day", "month", "year"):
        response = _client().get(f"/api/v1/insights/alerts?horizon={horizon}")
        assert response.status_code == 200, horizon
        body = response.json()
        assert body["horizon"] == horizon


def test_alerts_route_rejects_unknown_horizon() -> None:
    response = _client().get("/api/v1/insights/alerts?horizon=week")
    assert response.status_code == 422


def test_alerts_route_accepts_window_min_1440() -> None:
    """F-097: window_min=1440 (=1 день) теперь допустим (раньше было ≤120)."""
    response = _client().get("/api/v1/insights/alerts?window_min=1440")
    assert response.status_code == 200
    assert response.json()["window_min"] == 1440


def test_alerts_payload_alert_shape_when_present() -> None:
    """Alerts in the payload follow the OverloadAlert shape (when non-empty)."""
    response = _client().get("/api/v1/insights/alerts?window_min=30")
    body = response.json()
    if body["alerts"]:
        alert = body["alerts"][0]
        assert "stop_id" in alert
        assert "route_id" in alert
        assert "route_name" in alert
        assert "predicted_load_pct" in alert
        assert "time_to_overload_min" in alert
        assert "severity" in alert
        assert alert["severity"] in {"info", "warning", "critical"}
