"""Tests for MCP tools (T-200).

Backend может быть недоступен — поэтому mock'аем httpx.AsyncClient.get.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.tools import (
    TOOL_DISPATCH,
    TOOLS,
    dispatch_tool,
    get_historical_for_route,
    get_predictions_for_route,
    run_python_sandbox,
)
import pytest


def _make_mock_response(json_data: dict, status_code: int = 200):
    """Создаёт fully-async mock httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.json = MagicMock(return_value=json_data)
    if status_code < 400:
        response.raise_for_status = MagicMock(return_value=None)
    else:
        import httpx

        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"HTTP {status_code}", request=MagicMock(), response=response
            )
        )
    # .get() возвращает coroutine → обернём в AsyncMock
    async_coro = AsyncMock(return_value=response)
    return async_coro


# === Direct sandbox tests (no backend) ===


@pytest.mark.asyncio
async def test_run_python_sandbox_success() -> None:
    """Sandbox tool работает."""
    result = await run_python_sandbox("print('ok')")
    assert result["success"] is True
    assert "ok" in result["stdout"]


@pytest.mark.asyncio
async def test_run_python_sandbox_failure() -> None:
    """Sandbox tool ловит SyntaxError."""
    result = await run_python_sandbox("def x(:")
    assert result["success"] is False
    assert "SyntaxError" in result["error"]


@pytest.mark.asyncio
async def test_run_python_sandbox_forbidden() -> None:
    """Sandbox tool блокирует subprocess."""
    result = await run_python_sandbox("import subprocess")
    assert result["success"] is False
    assert "subprocess" in result["error"]


# === Tools with mocked backend ===


@pytest.mark.asyncio
async def test_get_predictions_for_route_with_mock() -> None:
    """Predictions tool: парсит JSON от backend."""
    mock_data = {
        "route_id": 7,
        "points": [{"period_start": "2025-11-01T08:00:00", "value": 50.0}],
    }
    with patch("app.tools.httpx.AsyncClient") as MockClient:
        client_instance = MockClient.return_value.__aenter__.return_value
        client_instance.get = _make_mock_response(mock_data)

        result = await get_predictions_for_route(
            route_id=7, from_date="2025-11-01", to_date="2025-11-02"
        )
        assert result["route_id"] == 7
        assert len(result["points"]) == 1


@pytest.mark.asyncio
async def test_get_historical_for_route_with_mock() -> None:
    """Historical tool: парсит JSON."""
    mock_data = {
        "route_id": 7,
        "points": [
            {"period_start": "2025-09-01", "value": 100.0},
            {"period_start": "2025-09-02", "value": 110.0},
        ],
    }
    with patch("app.tools.httpx.AsyncClient") as MockClient:
        client_instance = MockClient.return_value.__aenter__.return_value
        client_instance.get = _make_mock_response(mock_data)

        result = await get_historical_for_route(
            route_id=7, from_date="2025-09-01", to_date="2025-09-30"
        )
        assert result["route_id"] == 7
        assert len(result["points"]) == 2


@pytest.mark.asyncio
async def test_dispatch_tool_unknown() -> None:
    """Unknown tool → error message."""
    result = await dispatch_tool("nonexistent_tool", {})
    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_dispatch_tool_bad_arguments() -> None:
    """Tool с неправильными args → error."""
    result = await dispatch_tool("get_predictions_for_route", {})
    assert "error" in result
    assert "Bad arguments" in result["error"]


# === Tool registry ===


def test_all_tools_have_required_fields() -> None:
    """Каждый tool должен иметь name, description, input_schema."""
    for name, spec in TOOLS.items():
        assert "name" in spec
        assert "description" in spec
        assert "input_schema" in spec
        assert spec["name"] == name


def test_all_tools_have_implementations() -> None:
    """Каждый tool в TOOLS должен быть в TOOL_DISPATCH."""
    for name in TOOLS:
        assert name in TOOL_DISPATCH, f"No implementation for {name}"
