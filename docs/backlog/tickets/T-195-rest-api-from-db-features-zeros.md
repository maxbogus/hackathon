---
id: T-195
phase: 3
title: REST API endpoints — historical + predictions (DB) + features + zeros (T-195)
priority: P0
effort: 3
unit: hours
rice:
  R: 5
  I: 2
  C: 0.95
  score: 3.17
depends_on: [T-194]
blocks: [T-196, T-197]
tags: [backend, api, rest, database, features, zeros, csv-export]
status: done
created: 2026-09-26
updated: 2026-09-26
assignee: ""
---

## Context

T-194 дал PostgreSQL schema + alembic. Теперь нужны REST endpoints,
которые позволят frontend-у (T-196) показывать historical данные,
прогнозы из БД с фильтрацией, и переключать feature toggles/zero
overrides через UI.

## Acceptance Criteria

- [x] `apps/backend/app/db.py` — async engine + session factory + get_db()
- [x] `app/api/historical.py` — GET /api/v1/historical/{route_id} с day/hour aggregation
- [x] `app/api/historical.py` — GET /api/v1/historical (list routes)
- [x] `app/api/features.py` — GET /api/v1/features (list toggles + zeros)
- [x] `app/api/features.py` — POST /api/v1/features/{name}/toggle
- [x] `app/api/features.py` — POST /api/v1/zeros/{name}/toggle (с params)
- [x] `app/api/predictions_db.py` — GET /api/v1/predictions/db/{route_id} с фильтрами
- [x] `app/api/predictions_db.py` — GET /api/v1/predictions/export.csv (best params)
- [x] Default filters берутся из feature_toggles + zero_overrides (zero=ON, feature_set=with_all)
- [x] Pydantic schemas для всех endpoints
- [x] 14 unit tests (sqlite in-memory + dependency override)
- [x] OpenAPI регенерирован (16 paths)
- [x] Orval TS типы регенерированы
- [x] ruff: 0 errors

## Endpoints

| Method | Path | Описание |
|---|---|---|
| GET | `/api/v1/historical/{route_id}?from&to&granularity` | Historical boardings |
| GET | `/api/v1/historical` | List route_id с historical данными |
| GET | `/api/v1/features` | List all feature_toggles + zero_overrides |
| POST | `/api/v1/features/{name}/toggle` | {enabled: bool} |
| POST | `/api/v1/zeros/{name}/toggle` | {enabled: bool, params?: dict} |
| GET | `/api/v1/predictions/db/{route_id}?from&to&model_id&feature_set&zeros_applied&coef_*` | Прогнозы из БД |
| GET | `/api/v1/predictions/export.csv?from&to&...` | CSV download (clinerule 23) |

## Default behaviour (best submission)

`/predictions/export.csv` без query params возвращает:
- `feature_set=with_all` (use_poi/weather/events ON, use_traffic OFF)
- `zeros_applied=True` (zero_route_5 + zero_night_pred_cap ON)
- `coef_weather=coef_event=coef_season=1.0`
- → соответствует F-083 best (0.83455 platform score)

## CSV format (clinerule 23)

```
route;date;hour;prediction
7;2025-11-01;8;50.50
11;2025-11-01;8;50.50
```

- separator: `;`
- 4 колонки: route, date (YYYY-MM-DD), hour (0-23), prediction
- header НЕ включён (для совместимости с ml platform scoring)
- Headers ответа: `Content-Disposition`, `X-Row-Count`, `X-CSV-MD5`

## Verification

```bash
# 1. Tests
uv --directory apps/backend run pytest tests/test_api_t195.py -v --no-cov
# → 14 passed

# 2. OpenAPI регенерирован
python apps/backend/scripts/export_openapi.py
# → ✅ Exported OpenAPI (16 paths)

# 3. Orval TS
cd apps/frontend && yarn orval --config orval.config.ts
# → 🎉 Your OpenAPI spec has been converted into ready to use orval!

# 4. Lint
uv run ruff check apps/backend/
# → All checks passed!

# 5. Endpoints inventory
uv run python -c "
from app.main import create_app
app = create_app()
for p in sorted(app.openapi()['paths'].keys()):
    print(p)
"
# → 16 paths, включая новые: /historical, /features, /predictions/db, /predictions/export.csv
```

## Status

`done` (RED→GREEN→REFACTOR завершён в этой сессии)
