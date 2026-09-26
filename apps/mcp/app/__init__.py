"""Transit-AI MCP server (T-200).

MCP 2.0 (Model Context Protocol) сервер с aggregation tools.
Позволяет LLM-агентам (Claude Desktop, Cline, AI Gateway) вызывать
инструменты для анализа данных Transit-AI.

Tools:
  - get_predictions_for_route — прогноз по маршруту из БД
  - get_historical_for_route — исторические данные
  - get_top_routes_by_traffic — top-N маршрутов
  - get_validation_report — последний отчёт валидации
  - run_python_sandbox — выполнить Python в sandbox (T-199)

Паттерн server.py адаптирован из ~/Repositories/lawcopilot/mcp_browser/server.py
(НЕ копия, а свой код с теми же базовыми принципами: Server/Tool/TextContent
через mcp SDK stdio JSON-RPC).

Usage:
    cd apps/mcp && uv run python -m app.server
"""

from app.tools import TOOL_DISPATCH, TOOLS, dispatch_tool

__all__ = ["TOOLS", "TOOL_DISPATCH", "dispatch_tool"]
