# 02-architecture.md — Архитектура монорепо

## Монорепо apps/*

```
hackathon/
├── apps/
│   ├── backend/         # FastAPI :8000 (Богуславский)
│   ├── frontend/        # Vite/React :5173 (Баев)
│   ├── assistant/       # LLM ассистент (LiteLLM, lawcopilot-паттерн)
│   └── mcp/             # MCP-сервер (stdio JSON-RPC, черновик)
├── ml/                  # ML скрипты (вне Docker)
└── docs/                # документация, ledger, backlog, схемы
```

## Workspace boundaries

| Module | Может импортировать | Не может |
|---|---|---|
| `apps/backend` | `apps/backend.*`, контракты из `docs/schemas/` | `apps/frontend`, `apps/assistant`, `ml.transit_ai.models` (только контракт через JSON Schema!) |
| `apps/frontend` | только сгенерированные хуки из `apps/frontend/src/generated/` | ничего из `apps/*`, ничего из `ml/` |
| `apps/assistant` | `apps/backend.forecast` (опционально), `docs/schemas/` | циклы с `apps/mcp` (tools дублируются намеренно) |
| `apps/mcp` | `docs/schemas/` | `apps/assistant` (MCP независим, tools дублируются) |
| `ml/transit_ai` | только stdlib + ML/numpy/pandas/torch | ничего из `apps/*` (ML не знает про API) |

## Contract flow

```
[ ML скрипт ]
   |
   | пишет артефакт по JSON Schema
   v
[ ml/artifacts/<model_id>/meta.json + model.pkl + ... ]
   |
   | читается forecast/loader.py
   v
[ FastAPI endpoint /api/v1/predictions/stop/{id} ]
   |
   | генерирует OpenAPI
   v
[ docs/api/openapi.json ]
   |
   | Orval генерит хуки
   v
[ apps/frontend/src/generated/api.ts ]
   |
   | используется в React-компонентах
   v
[ Dashboard: useGetPredictionsStopStopId(42) → график ]
```

## ML artefacts contract

JSON Schema в `docs/schemas/prediction_artifact.schema.json`.
Валидация в `apps/backend/forecast/loader.py` через `jsonschema`.
Если артефакт не валиден — `make evaluate` упадёт с понятной ошибкой.

## Модели

| Модель | Kind | Размер | Откуда код |
|---|---|---|---|
| `BaselineMean` | baseline | n/a | свой |
| `XGBoost` | xgboost | n/a | свой |
| `GRU` (PyTorch + attention pooling) | neural | ~100K params | адаптация `contest/ecup26-user-value/scripts/experiment_neural_gru.py` |
| `Hybrid` (GRU + LGBM blend в log-space) | hybrid | ~200K | адаптация `experiment_blend_gru_lgbm.py` |
| `MonteCarlo` | simulation | n/a (использует любую модель + шум) | копия `~/Repositories/montecarlo/` |

## Горизонты

| Horizon | Granularity | Модель |
|---|---|---|
| day | hour | GRU + Hybrid |
| month | day | XGBoost + Hybrid (blend) |
| year | month | Monte Carlo (средняя по симуляциям) |

## Подробнее

- ML pipeline: `.clinerules/10-ml-as-scripts.md`
- Контракты: `.clinerules/08-contracts-and-artifacts.md`
- Ассистент: `.clinerules/11-assistant-pattern.md`
- MCP: `.clinerules/12-mcp-draft.md`
