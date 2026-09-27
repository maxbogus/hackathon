# Точки входа API (производное от docs/api/openapi.json)

| Метод | Путь | Тег | Описание |
|---|---|---|---|
| GET | `/` | meta | Root |
| GET | `/api/v1/features` | features | List all feature toggles and zero overrides |
| POST | `/api/v1/features/{name}/toggle` | features | Toggle a feature on/off |
| GET | `/api/v1/geo/routes` | geo | T-227: Справочник остановок маршрутов (для карты) |
| GET | `/api/v1/healthz` | health | Liveness probe |
| GET | `/api/v1/historical` | historical | List available routes with historical data |
| GET | `/api/v1/historical/export.csv` | historical | Historical actuals as CSV (T-220) |
| GET | `/api/v1/historical/load` | load-summary | T-218: Summary actuals — avg load per route (block 'kak bylo', fallback MAX period) |
| GET | `/api/v1/historical/{route_id}` | historical | Historical boardings (actuals) for a route |
| GET | `/api/v1/insights/alerts` | insights | Get Overload Alerts |
| GET | `/api/v1/models` | models | List all known ML artifacts |
| GET | `/api/v1/models/active` | predictions | Get active model info |
| POST | `/api/v1/pipeline/full` | pipeline | Trigger ml_pipeline.full_pipeline (T-198/T-230) |
| GET | `/api/v1/pipeline/status/{task_id}` | pipeline | Get Celery task status (T-198) |
| GET | `/api/v1/predictions/active` | predictions-runs | T-230: параметры активного набора (source of truth для UI) |
| GET | `/api/v1/predictions/db/{route_id}` | predictions-db | Predictions for route (from DB with feature_set / zeros filters) |
| GET | `/api/v1/predictions/eta` | predictions | Get next N upcoming trams at a stop (ETA + predicted load) |
| GET | `/api/v1/predictions/export.csv` | predictions-db | Export predictions as CSV (default params = best submission) |
| GET | `/api/v1/predictions/export.xlsx` | predictions-db | Export predictions as XLSX (T-206: альтернатива CSV для аналитиков) |
| GET | `/api/v1/predictions/load` | load-summary | T-218: Summary predictions — avg load per route (block 'kak budet') |
| POST | `/api/v1/predictions/regenerate` | predictions-runs | T-230: сгенерировать новый набор |
| POST | `/api/v1/predictions/restore-etalon` | predictions-runs | T-230: вернуть эталонный набор как активный |
| GET | `/api/v1/predictions/runs` | predictions-runs | T-230: список запусков генерации |
| GET | `/api/v1/predictions/runs/{run_id}` | predictions-runs | T-230: статус запуска + кандидат (при Celery SUCCESS) |
| POST | `/api/v1/predictions/runs/{run_id}/ingest` | predictions-runs | T-230: загрузить CSV кандидата в БД (и опционально активировать) |
| POST | `/api/v1/predictions/runs/{run_id}/reject` | predictions-runs | T-230: отклонить кандидата (оставить эталон/текущий набор) |
| GET | `/api/v1/predictions/status` | predictions-status | Predictions DB status (T-198) |
| GET | `/api/v1/predictions/stop/{stop_id}` | predictions | Get ridership predictions for a stop |
| GET | `/api/v1/readyz` | health | Readiness probe |
| GET | `/api/v1/version` | health | Build info |
| POST | `/api/v1/zeros/{name}/toggle` | features | Toggle a zero override on/off |

Swagger UI: `http://localhost:8000/docs` · OpenAPI: `http://localhost:8000/openapi.json`
Всего путей: 31.
