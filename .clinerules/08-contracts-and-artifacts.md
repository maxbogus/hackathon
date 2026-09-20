# 08-contracts-and-artifacts.md — Контракты (JSON Schema, OpenAPI, MCP)

## Почему контракты важны

На хакатоне **нет данных заранее**. Без контракта:
- API ломается при изменении формата данных
- ML pipeline падает на неожиданных колонках
- Frontend не может зарелизиться пока backend не стабилизируется

С контрактами:
- Backend, ML, Frontend развиваются параллельно
- Замена источника данных = 1 файл (адаптер)
- Orval гарантирует типобезопасность фронта

## 1. ML artefact contract

**Файл:** `docs/schemas/prediction_artifact.schema.json`
**Валидация:** `apps/backend/forecast/loader.py` через `jsonschema`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ModelArtifact",
  "type": "object",
  "required": ["model_id", "kind", "version", "trained_at", "metrics", "files"],
  "properties": {
    "model_id": {"type": "string", "pattern": "^[a-z0-9_-]+$"},
    "kind": {"enum": ["baseline", "xgboost", "gru", "hybrid", "montecarlo"]},
    "version": {"type": "string", "pattern": "^v\\d+\\.\\d+\\.\\d+$"},
    "trained_at": {"type": "string", "format": "date-time"},
    "git_commit": {"type": "string"},
    "train_data_hash": {"type": "string"},
    "seed": {"type": "integer"},
    "horizons": {"type": "array", "items": {"enum": ["day", "month", "year"]}},
    "granularities": {"type": "array", "items": {"enum": ["hour", "day", "month"]}},
    "metrics": {
      "type": "object",
      "properties": {
        "rmsle": {"type": "number"},
        "mae": {"type": "number"},
        "mape": {"type": "number"}
      },
      "required": ["rmsle"]
    },
    "calibration": {
      "type": "object",
      "properties": {
        "kind": {"enum": ["bucket", "segmental", "shrink"]},
        "edges": {"type": "array", "items": {"type": "number"}},
        "biases": {"type": "array", "items": {"type": "number"}}
      }
    },
    "files": {
      "type": "object",
      "properties": {
        "model": {"type": "string"},
        "preprocessor": {"type": "string"},
        "feature_names": {"type": "string"}
      },
      "required": ["model"]
    }
  }
}
```

## 2. Predictions contract (parquet schema)

**Файл:** `docs/schemas/predictions.schema.json`

```python
# ml/transit_ai/data/schemas.py
PREDICTIONS_SCHEMA = {
    "period_start": "datetime64[ns]",
    "period_end": "datetime64[ns]",
    "stop_id": "int64",
    "route_id": "int64",
    "value": "float64",
    "lower": "float64",
    "upper": "float64",
    "horizon": "object",       # day | month | year
    "granularity": "object",   # hour | day | month
    "model_id": "object",
    "scenario_id": "object",   # optional
}
```

## 3. OpenAPI contract

**Файл:** `docs/api/openapi.json` (генерируется из FastAPI)
**Версионирование:** backend-first. Меняем FastAPI routes/schemas → `make api-gen`.

Pre-commit hook проверяет что `openapi.json` свежий (через `scripts/check_openapi.py`).

## 4. MCP tools contract

**Файл:** `apps/mcp/mcp.json` (регистрация) + каждый tool с JSON Schema для inputs/outputs.

```python
# apps/mcp/tools/predictions.py
TOOL_SCHEMA = {
    "name": "get_predictions_for_route",
    "description": "Получить прогноз пассажиропотока для маршрута",
    "input_schema": {
        "type": "object",
        "properties": {
            "route_id": {"type": "integer"},
            "from": {"type": "string", "format": "date"},
            "to": {"type": "string", "format": "date"},
            "horizon": {"enum": ["day", "month", "year"]}
        },
        "required": ["route_id", "horizon"]
    }
}
```

## 5. Frontend TS contract

**Файл:** `apps/frontend/src/generated/api.ts` (генерируется Orval)
**Файл:** `apps/frontend/src/api/customInstance.ts` (custom fetch wrapper)

Pre-push hook проверяет что `generated/` синхронизирован с `openapi.json`.

## Workflow контрактов

```
1. Меняем контракт (FastAPI / JSON Schema)
2. Регенерируем downstream артефакты
3. Прогоняем тесты
4. Коммитим ВСЁ вместе
```

Пример:
```bash
# Меняем predictions endpoint
# ... правим apps/backend/app/api/predictions.py
make api-gen   # обновляет docs/api/openapi.json
make fe-gen    # обновляет apps/frontend/src/generated/
make check-all
git add apps/ docs/api/
git commit -m "feat(backend): add horizon param to predictions (T-043)"
```
