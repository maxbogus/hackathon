"""MCP 2.0 server entry point (T-200).

stdio JSON-RPC через mcp SDK. Паттерн адаптирован из
~/Repositories/lawcopilot/mcp_browser/server.py.

Запуск:
    cd apps/mcp && uv run python -m app.server
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.tools import TOOLS, dispatch_tool

server = Server("transit-ai-mcp")


async def main() -> None:
    """Запуск stdio сервера с обработчиками tools/list и tools/call."""
    from mcp.types import CallToolRequest, ListToolsRequest, TextContent, Tool

    @server.request_handler(ListToolsRequest)
    async def handle_list_tools(_req):
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["input_schema"],
            )
            for t in TOOLS.values()
        ]

    @server.request_handler(CallToolRequest)
    async def handle_call_tool(req: CallToolRequest):
        name = req.params.name
        arguments = req.params.arguments or {}
        result = await dispatch_tool(name, arguments)
        return [
            TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, default=str),
            )
        ]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
