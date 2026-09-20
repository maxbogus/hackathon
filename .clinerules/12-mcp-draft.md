# 12-mcp-draft.md — MCP-сервер (черновик)

## Что это

MCP (Model Context Protocol) — это протокол для подключения инструментов к AI-агентам
(Claude Desktop, Cline, AI Gateway). Мы делаем **черновик** — 5–7 инструментов
поверх assistant tools, чтобы ассистент был доступен из Claude/Cline.

## Почему draft, не полный

- На хакатоне 90% ценности — дашборд + прогнозы
- LLM-ассистент — дифференциатор, но не критичен для победы
- Полноценный MCP = +1-2 дня работы, лучше потратить на тюнинг моделей
- Делаем рабочий черновик, расширяем если останется время

## Что входит

### Tools (5-7 штук)

| Tool | Что делает | Источник |
|---|---|---|
| `get_predictions_for_route` | Прогноз по маршруту | GET /api/v1/predictions/route/{id} |
| `get_top_congested_stops` | Топ перегруженных остановок в области/времени | GET /api/v1/insights/top_congested |
| `get_anomalies` | Аномалии за период | GET /api/v1/insights/anomalies |
| `list_models` | Список обученных моделей | GET /api/v1/models |
| `activate_model` | Активировать модель | POST /api/v1/models/{id}/activate |
| `run_simulation` | Monte Carlo "что если" | POST /api/v1/scenarios (Monte Carlo на backend) |
| `get_validation_report` | Отчёт по валидации данных | GET /data/validation_reports/latest.json |

### Транспорт

- **stdio** (по умолчанию, для локального Claude/Cline)
- HTTP+SSE (опционально, для удалённого Claude через Cloudflared)

### Паттерн

Из `mcp-servers/celery-batch-mcp/server.py`:

```python
# apps/mcp/server.py
import sys
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Импорты наших tools (JSON-RPC версии)
from tools.predictions import get_predictions_for_route
from tools.insights import get_top_congested_stops, get_anomalies
from tools.models import list_models, activate_model
from tools.scenarios import run_simulation
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
                    "from": {"type": "string", "format": "date"},
                    "to": {"type": "string", "format": "date"},
                    "horizon": {"enum": ["day", "month", "year"]},
                },
                "required": ["route_id"],
            },
        },
    },
    # ... остальные tools
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

## Регистрация

`apps/mcp/mcp.json`:

```json
{
  "mcpServers": {
    "transit-ai": {
      "command": "uv",
      "args": ["--directory", "/home/maxbogus/Repositories/hackathon/apps/mcp", "run", "python", "server.py"],
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "ARTIFACTS_DIR": "/home/maxbogus/Repositories/hackathon/ml/artifacts",
        "DATA_DIR": "/home/maxbogus/Repositories/hackathon/data",
      }
    }
  }
}
```

Подключение в Claude Desktop / Cline: добавить содержимое `mcp.json` в
`~/.config/claude-desktop/mcp.json` (Linux) или аналог.

## Тестирование

```bash
# 1. Поднять backend
make up

# 2. Запустить MCP (stdio, для теста)
make mcp-run

# 3. Из Claude/Cline попробовать:
#    "Какой прогноз по маршруту 10 на завтра?"
#    → должен вызвать get_predictions_for_route(10)
#    → вернуть данные
```

Из `lawcopilot/ai/skills/mcp-v3-mounting.md`:

> Правильный признак включения: 401 при выключенном флаге, а НЕ 200.
> Если крепление выключено, SPA-заглушка отвечает 200 OK с HTML — это false positive.

## Что НЕ делаем (в рамках черновика)

- ❌ HTTP+SSE транспорт (только stdio)
- ❌ JWT авторизация (для локального dev не нужна)
- ❌ Rate limiting
- ❌ Кэширование tool responses (assistant сам кэширует в Redis)
- ❌ Историю вызовов (mcp_call_log) — для хакатона не критично

## Когда расширять

Если на хакатоне осталось время:
- + Инструменты для сравнения сценариев (`compare_scenarios`)
- + RAG по регламентам (если будет документация)
- + HTTP+SSE для демо через Cloudflared
- + Журнал вызовов в SQLite
