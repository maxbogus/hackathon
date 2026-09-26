"""Aggregation tools для MCP (T-200).

Возвращают данные из Transit-AI backend через HTTP.
Реализуют типичные аналитические запросы, которые нужны LLM-агентам.

Паттерн адаптирован из ~/Repositories/lawcopilot/mcp_browser/server.py —
но это свой код с теми же базовыми принципами (Server/Tool/TextContent
через mcp SDK stdio JSON-RPC).
"""

from __future__ import annotations

from typing import Any

import httpx

BACKEND_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0


async def _get(path: str, params: dict | None = None) -> dict[str, Any]:
    """Helper: GET к backend с обработкой ошибок."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        try:
            r = await client.get(f"{BACKEND_URL}{path}", params=params or {})
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text}
        except httpx.RequestError as e:
            return {"error": "Backend unreachable", "detail": str(e)}


# ===========================================================================
# Tools (реестр для MCP server)
# ===========================================================================

TOOLS: dict[str, dict] = {
    "get_predictions_for_route": {
        "name": "get_predictions_for_route",
        "description": (
            "Получить прогноз пассажиропотока для маршрута из БД. "
            "Поддерживает фильтры: feature_set, zeros_applied. "
            "Возвращает массив точек {period_start, value, ...}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "route_id": {"type": "integer", "minimum": 1},
                "from_date": {"type": "string", "format": "date"},
                "to_date": {"type": "string", "format": "date"},
                "feature_set": {
                    "type": "string",
                    "enum": ["baseline", "with_poi", "with_all"],
                    "default": None,
                },
                "zeros_applied": {"type": "boolean", "default": None},
            },
            "required": ["route_id", "from_date", "to_date"],
        },
    },
    "get_historical_for_route": {
        "name": "get_historical_for_route",
        "description": (
            "Получить исторические данные (actuals) для маршрута. "
            "Поддерживает granularity: hour|day."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "route_id": {"type": "integer", "minimum": 1},
                "from_date": {"type": "string", "format": "date"},
                "to_date": {"type": "string", "format": "date"},
                "granularity": {
                    "type": "string",
                    "enum": ["hour", "day"],
                    "default": "day",
                },
            },
            "required": ["route_id", "from_date", "to_date"],
        },
    },
    "get_top_routes_by_traffic": {
        "name": "get_top_routes_by_traffic",
        "description": (
            "Top-N маршрутов по среднему трафику за период. "
            "Используется для ответа на вопрос 'какие маршруты самые загруженные'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_date": {"type": "string", "format": "date"},
                "to_date": {"type": "string", "format": "date"},
                "n": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
            },
            "required": ["from_date", "to_date"],
        },
    },
    "get_validation_report": {
        "name": "get_validation_report",
        "description": (
            "Получить последний отчёт валидации данных (если есть). "
            "Inventory report — статистика по routes/stops/boardings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    "run_python_sandbox": {
        "name": "run_python_sandbox",
        "description": (
            "Выполнить Python код в изолированном sandbox (T-199). "
            "Запрещены: subprocess, socket, eval, exec. "
            "Timeout: 30 сек. Возвращает stdout + result + error."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python код для выполнения",
                },
                "timeout_sec": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 60,
                    "default": 30,
                },
            },
            "required": ["code"],
        },
    },
}


# ===========================================================================
# Tool implementations
# ===========================================================================


async def get_predictions_for_route(
    route_id: int,
    from_date: str,
    to_date: str,
    feature_set: str | None = None,
    zeros_applied: bool | None = None,
) -> dict[str, Any]:
    """GET /api/v1/predictions/db/{route_id}."""
    params: dict[str, Any] = {"from": from_date, "to": to_date}
    if feature_set:
        params["feature_set"] = feature_set
    if zeros_applied is not None:
        params["zeros_applied"] = "true" if zeros_applied else "false"
    return await _get(f"/api/v1/predictions/db/{route_id}", params)


async def get_historical_for_route(
    route_id: int,
    from_date: str,
    to_date: str,
    granularity: str = "day",
) -> dict[str, Any]:
    """GET /api/v1/historical/{route_id}."""
    return await _get(
        f"/api/v1/historical/{route_id}",
        {"from": from_date, "to": to_date, "granularity": granularity},
    )


async def get_top_routes_by_traffic(
    from_date: str,
    to_date: str,
    n: int = 5,
) -> dict[str, Any]:
    """Получить все маршруты и отсортировать по суммарному трафику."""
    routes = await _get("/api/v1/historical")
    routes_list = routes.get("routes", [])

    results = []
    for route_id in routes_list:
        data = await get_historical_for_route(route_id, from_date, to_date, "day")
        if "error" in data:
            continue
        points = data.get("points", [])
        total = sum(p.get("value", 0) for p in points)
        avg = total / len(points) if points else 0
        results.append(
            {
                "route_id": route_id,
                "total_boardings": round(total, 1),
                "avg_per_day": round(avg, 1),
                "days_with_data": len(points),
            }
        )

    results.sort(key=lambda x: x["total_boardings"], reverse=True)
    return {"top_n": results[:n], "total_routes": len(results)}


async def get_validation_report() -> dict[str, Any]:
    """Заглушка: возвращает meta о validation report."""
    from pathlib import Path

    report_path = Path("data/validation_reports/inventory.json")
    if not report_path.exists():
        return {"status": "no_report", "message": "Run `make inventory` to generate"}
    try:
        import json

        data = json.loads(report_path.read_text())
        return {"status": "ok", "report": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def run_python_sandbox(code: str, timeout_sec: float = 30.0) -> dict[str, Any]:
    """Выполнить код в T-199 sandbox.

    Импортируем transit_ai_sandbox динамически — может быть не установлен
    если MCP запущен standalone без workspace.
    """
    try:
        from transit_ai_sandbox.executor import run_in_sandbox
    except ImportError:
        # Fallback: inline минимальный sandbox (если workspace не настроен)
        import ast
        import contextlib
        import io
        import time

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"success": False, "error": f"SyntaxError: {e}", "stdout": "", "duration_ms": 0}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in {"subprocess", "socket", "urllib"}:
                        return {
                            "success": False,
                            "error": f"Forbidden import: {a.name}",
                            "stdout": "",
                            "duration_ms": 0,
                        }
        buf = io.StringIO()
        start = time.time()
        safe_builtins = (
            {k: v for k, v in __builtins__.items() if k not in {"exec", "eval", "open"}}
            if isinstance(__builtins__, dict)
            else {}
        )
        try:
            with contextlib.redirect_stdout(buf):
                exec(code, {"__builtins__": safe_builtins})
            return {
                "success": True,
                "stdout": buf.getvalue(),
                "return_value": None,
                "error": "",
                "duration_ms": round((time.time() - start) * 1000, 2),
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": buf.getvalue(),
                "error": f"{type(e).__name__}: {e}",
                "duration_ms": round((time.time() - start) * 1000, 2),
            }

    result = run_in_sandbox(code, timeout_sec=timeout_sec)
    return {
        "success": result.success,
        "stdout": result.stdout,
        "return_value": result.return_value,
        "error": result.error,
        "duration_ms": round(result.duration_ms, 2),
    }


# ===========================================================================
# Dispatcher (для MCP server)
# ===========================================================================

TOOL_DISPATCH: dict[str, Any] = {
    "get_predictions_for_route": get_predictions_for_route,
    "get_historical_for_route": get_historical_for_route,
    "get_top_routes_by_traffic": get_top_routes_by_traffic,
    "get_validation_report": get_validation_report,
    "run_python_sandbox": run_python_sandbox,
}


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Вызывает tool по имени с arguments."""
    if name not in TOOL_DISPATCH:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await TOOL_DISPATCH[name](**arguments)
    except TypeError as e:
        return {"error": f"Bad arguments: {e}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
