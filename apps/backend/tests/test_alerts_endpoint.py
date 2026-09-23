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
    """window_min > 120 (4-hour horizon) is rejected — slack bound for dispatcher UI."""
    response = _client().get("/api/v1/insights/alerts?window_min=600")
    assert response.status_code == 422


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
