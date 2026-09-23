---
id: T-139
phase: 6
title: apps/mcp — stdio JSON-RPC сервер с 5-7 tools (черновик MCP для Claude Desktop)
priority: P2
effort: 4
unit: hours
rice:
  R: 4
  I: 2.0
  C: 0.8
  score: 1.6
depends_on: [T-138]
blocks: []
tags: [mcp, json-rpc, stdio, hackathon, differentiator, ai-agent]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-139: apps/mcp — stdio JSON-RPC сервер с 5-7 tools (черновик MCP)

## Context

Clinerule 12-mcp-draft.md подробно описывает паттерн MCP-сервера. D-002 зафиксировал
mcp-servers/celery-batch-mcp как шаблон.

**Текущее состояние (КРИТИЧНО):**
- apps/mcp/ — есть только пустые tools/ и tests/.
- Нет apps/mcp/server.py — **главный файл MCP отсутствует**.
- Нет apps/mcp/mcp.json — **регистрация для Claude Desktop отсутствует**.

MCP (Model Context Protocol) — стандарт для AI-агентов (Claude Desktop, Cline, AI Gateway).
С нашим MCP-сервером диспетчер сможет из Claude Desktop спросить «какой прогноз по маршруту 7?».

## Acceptance Criteria

- [ ] Установлена зависимость: mcp>=2.0.0
- [ ] Создан apps/mcp/server.py — stdio JSON-RPC сервер (из clinerule 12)
- [ ] Создан apps/mcp/mcp.json — регистрация для Claude Desktop / Cline
- [ ] Реализованы **5 tools** (минимум):
  - [ ] get_predictions_for_route(route_id, horizon)
  - [ ] get_top_congested_stops(window_min, n)
  - [ ] list_models()
  - [ ] activate_model(model_id)
  - [ ] get_validation_report()
- [ ] Каждый tool имеет JSON Schema для input/output
- [ ] Тесты: apps/mcp/tests/test_server.py (3+ кейса)
- [ ] Документация: apps/mcp/README.md (как подключить к Claude Desktop)
- [ ] Makefile target mcp-run работает
- [ ] Smoke test: запустить make mcp-run, послать JSON-RPC запрос

## Technical Notes

Паттерн из clinerule 12:
```python
# apps/mcp/server.py
import sys
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.predictions import get_predictions_for_route
from tools.alerts import get_top_congested_stops
from tools.models import list_models, activate_model
from tools.validation import get_validation_report

app = Server("transit-ai-mcp")

TOOLS = {
    "get_predictions_for_route": {
        "fn": get_predictions_for_route,
        "schema": {
            "name": "get_predictions_for_route",
            "description": "Получить прогноз пассажиропотока для маршрута",
            "input_schema": {
                "type": "object",
                "properties": {
                    "route_id": {"type": "integer", "minimum": 1},
                    "horizon": {"enum": ["day", "month", "year"]},
                },
                "required": ["route_id"],
            },
        },
    },
    # ... остальные 4 tools
}

@app.list_tools()
async def list_tools():
    return [tool["schema"] for tool in TOOLS.values()]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    result = await TOOLS[name]["fn"](**arguments)
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

Регистрация для Claude Desktop (apps/mcp/mcp.json):
```json
{
  "mcpServers": {
    "transit-ai": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/maxbogus/Repositories/hackathon/apps/mcp",
        "run",
        "python",
        "server.py"
      ],
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "ARTIFACTS_DIR": "/home/maxbogus/Repositories/hackathon/ml/artifacts",
        "DATA_DIR": "/home/maxbogus/Repositories/hackathon/data"
      }
    }
  }
}
```

Tools берутся из T-138 (assistant tools) — переиспользуем.

## Verification

```bash
# 1. Зависимости
cd apps/mcp && uv sync

# 2. Type-check
cd apps/mcp && uv run mypy .

# 3. Tests
cd apps/mcp && uv run pytest tests/ -v

# 4. Live smoke (требует backend на :8000)
make up
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | make mcp-run
# Ожидаем: JSON со списком 5 tools

# 5. Tool call
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_predictions_for_route","arguments":{"route_id":7}},"id":2}' | make mcp-run
# Ожидаем: JSON с данными прогноза
```

## Beneficiary Impact

**Жюри (⭐⭐⭐⭐⭐)** — демо через Claude Desktop = wow-эффект.
**AI-агенты (⭐⭐⭐⭐)** — Cline / Claude Desktop / AI Gateway.
**Департамент (⭐⭐⭐)** — стандарт для AI-интеграции.

RICE: 1.6 — формально низкий, но самый яркий wow-эффект для жюри.
