---
id: T-194
phase: 3
title: PostgreSQL schema + alembic migrations (T-194)
priority: P0
effort: 3
unit: hours
rice:
  R: 4
  I: 2
  C: 0.9
  score: 2.40
depends_on: [T-193]
blocks: [T-195, T-196, T-197]
tags: [database, postgresql, alembic, sqlalchemy, backend, infrastructure]
status: done
created: 2026-09-26
updated: 2026-09-26
assignee: ""
---

## Context

T-193 (Celery pipeline) собирает данные и делает прогнозы, но без
персистентной БД результаты теряются между сессиями. Чтобы frontend
мог показывать historical+прогнозы и работать с feature toggles,
нужна PostgreSQL схема с alembic миграциями. Также TimescaleDB
hypertable для efficient time-range queries (clinerule 18).

## Acceptance Criteria

- [x] `apps/backend/alembic.ini` + `env.py` (async, SQLAlchemy 2.0)
- [x] `apps/backend/alembic/script.py.mako` (template для новых миграций)
- [x] 5 ORM моделей: Actual, Prediction, FeatureToggle, ZeroOverride, PredictionRun
- [x] Initial migration: 5 таблиц + indexes + seeds
- [x] TimescaleDB hypertable для actuals (best-effort, только postgres)
- [x] Seed defaults: 6 feature_toggles + 4 zero_overrides (F-051/F-060 best)
- [x] 8 unit тестов (sqlite in-memory)
- [x] Alembic upgrade/downgrade round-trip работает
- [x] Makefile: `db-upgrade / db-downgrade / db-revision / db-current / db-history`
- [x] ruff: 0 errors

## Tables

### actuals (historical boardings)
- `id`, `route_id`, `period_start`, `period_end`, `value`
- Index: `ix_actuals_route_period` (route_id, period_start)
- TimescaleDB hypertable на `period_start` (chunk=7 дней)

### predictions (ML результаты)
- 22 поля: route × period × value/lower/upper
- Метаданные: `model_id`, `model_kind`, `model_version`
- Конфиг: `feature_set`, `feature_flags` (JSON), `zeros_applied`, `zero_config` (JSON)
- Коэффициенты: `coef_weather`, `coef_event`, `coef_season`
- Lineage: `submission_id`, `git_commit`, `created_at`
- Indexes: route_period, model_feature, submission

### feature_toggles (UI toggles)
- `name` (unique): use_poi, use_traffic, use_weather, use_events, use_seasonal, use_lag
- `enabled`, `is_default` (для reset), `description`
- Seed: use_poi/weather/events/seasonal/lag = ON, use_traffic = OFF

### zero_overrides (zero-strategy toggles)
- `name` (unique): zero_route_5, zero_night_pred_cap, zero_weekend, zero_holidays
- `enabled`, `params` (JSON: pred_cap, hours, route_id, ...)
- Seed: zero_route_5 + zero_night_pred_cap = ON (как в F-051/F-060 best)

### prediction_runs (Celery task log)
- `celery_task_id`, `task_name`, `status`
- `params`, `result`, `holdout_wape_score`
- `manifest_path`, `csv_path` — для traceability

## Privacy

- Все таблицы `no-PII` (агрегированный трафик + метаданные)
- Не храним: паспорт, медданные, ФИО, IP-адреса
- Соответствует ФЗ-152 для пассажиропотока

## Verification

```bash
# 1. Tests
uv --directory apps/backend run pytest tests/test_models_t194.py -v --no-cov
# → 8 passed

# 2. Migration round-trip (sqlite для теста)
cd apps/backend
rm -f test.db
TRANSIT_AI_DATABASE_URL='sqlite+aiosqlite:///test.db' uv run python -m alembic upgrade head
TRANSIT_AI_DATABASE_URL='sqlite+aiosqlite:///test.db' uv run python -m alembic downgrade base
TRANSIT_AI_DATABASE_URL='sqlite+aiosqlite:///test.db' uv run python -m alembic upgrade head
# → all OK

# 3. Verify schema
TRANSIT_AI_DATABASE_URL='sqlite+aiosqlite:///test.db' uv run python -c "
import asyncio, sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
async def main():
    e = create_async_engine('sqlite+aiosqlite:///test.db')
    async with e.connect() as c:
        r = await c.execute(sa.text('SELECT name FROM feature_toggles ORDER BY name'))
        print([row[0] for row in r])
asyncio.run(main())
"
# → ['use_events', 'use_lag', 'use_poi', 'use_seasonal', 'use_traffic', 'use_weather']

# 4. Make targets
make db-upgrade    # apply migrations (need postgres running)
make db-history    # show migration log
make db-current    # current revision

# 5. Lint
uv run ruff check apps/backend/app/models/ apps/backend/tests/test_models_t194.py apps/backend/alembic/
# → All checks passed!
```

## Status

`done` (RED→GREEN→REFACTOR завершён в этой сессии)
