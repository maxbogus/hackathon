---
id: T-220
phase: 3
title: Backend /api/v1/historical/export.csv endpoint (CSV download из actuals)
priority: P0
effort: 1
unit: hours
rice:
  R: 3
  I: 2
  C: 0.7
  score: 4.2
depends_on: []
blocks: [T-221, T-222, T-223]
tags: [backend, csv, historical, clinerule-31]
status: ready
created: 2026-09-27
updated: 2026-09-27
assignee: ""
---

## Context

T-218 сделал summary endpoints `/predictions/load` и `/historical/load` (avg per route) и выяснилось,
что **avg даёт не то число, что нужно пассажиру**: AVG(value) для route 1 = 1007 чел/час — это
«среднее за час», а не «сколько за день». Пассажир хочет видеть «X чел в сутки поедет» = SUM за день.

Пользователь утвердил в act-mode (после F-099 «avg vs sum»): **PassengerMode получает сырой CSV
из БД и сам агрегирует SUM по маршруту за день**. Для этого нужен `/historical/export.csv` —
зеркало существующего `/predictions/export.csv`, но читает из таблицы `actuals`.

`/predictions/export.csv` уже работает (см. `apps/backend/app/api/predictions_db.py:133`),
отдаёт `route;period_start;period_end;value`. Нужна точная копия для actuals.

## Acceptance Criteria

- [ ] `GET /api/v1/historical/export.csv` возвращает `text/csv; charset=utf-8`
- [ ] Колонки: `route;date;hour;value` (4 столбца, **единый формат с predictions**, header первая строка)
- [ ] Без параметров: за весь диапазон actuals (`MIN(period_start)` до `MAX(period_start)`)
- [ ] С параметрами `?from=YYYY-MM-DD&to=YYYY-MM-DD` фильтрует `period_start >= from AND period_start < to`
- [ ] Пустая БД → пустой CSV (только header)
- [ ] OpenAPI свежий (`make api-gen` без ошибок, +1 path)
- [ ] Тесты `apps/backend/tests/test_historical_export.py`: 4+ passed
- [ ] `make check-all` зелёный

## RED (apps/backend/tests/test_historical_export.py)

```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.models import Actual
from datetime import datetime, UTC

@pytest.mark.asyncio
async def test_export_csv_returns_header_only_when_empty(session):
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/api/v1/historical/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.strip() == "route;period_start;period_end;value"

@pytest.mark.asyncio
async def test_export_csv_returns_seeded_rows(session):
    # seed 3 actuals rows for route 17
    session.add_all([
        Actual(route_id=17, period_start=datetime(2025, 10, 29, tzinfo=UTC),
               period_end=datetime(2025, 10, 30, tzinfo=UTC), value=100.0),
        Actual(route_id=17, period_start=datetime(2025, 10, 30, tzinfo=UTC),
               period_end=datetime(2025, 10, 31, tzinfo=UTC), value=200.0),
        Actual(route_id=17, period_start=datetime(2025, 10, 31, tzinfo=UTC),
               period_end=datetime(2025, 11, 1, tzinfo=UTC), value=300.0),
    ])
    await session.commit()
    async with AsyncClient(app=app, base_url="http://test") as c:
        r = await c.get("/api/v1/historical/export.csv")
    lines = r.text.strip().split("\n")
    assert lines[0] == "route;period_start;period_end;value"
    assert len(lines) == 4

@pytest.mark.asyncio
async def test_export_csv_respects_date_filter(session):
    # seed rows + GET ?from=...&to=... → только в окне
    ...

@pytest.mark.asyncio
async def test_export_csv_orders_by_period_start(session):
    # ORDER BY route_id, period_start
    ...
```

## GREEN (apps/backend/app/api/historical.py — добавить в конец)

```python
from fastapi.responses import Response

@router.get(
    "/historical/export.csv",
    summary="Historical actuals as CSV (T-220)",
    response_class=Response,
)
async def get_historical_csv(
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Тот же формат что и /predictions/export.csv: route;date;hour;value (header)."""
    stmt = select(Actual).order_by(Actual.route_id, Actual.period_start)
    if from_date is not None:
        stmt = stmt.where(Actual.period_start >= from_date)
    if to_date is not None:
        stmt = stmt.where(Actual.period_start < to_date)
    rows = (await session.execute(stmt)).scalars().all()
    lines = ["route;period_start;period_end;value"]
    for r in rows:
        lines.append(f"{r.route_id};{r.period_start.date().isoformat()};{r.period_start.hour};{r.value:.2f}")
    return Response(content="\n".join(lines) + "\n", media_type="text/csv; charset=utf-8")
```

## Verification

```bash
curl -sS http://localhost:8000/api/v1/historical/export.csv | head -2
# ожидаем: route;period_start;period_end;value\n<route>;<iso>;<iso>;<float>
curl -sS http://localhost:8000/api/v1/historical/export.csv | wc -l
# ожидаем: ≥68801 + 1 (header)

cd apps/backend && uv run pytest tests/test_historical_export.py -v --no-cov
make api-gen
make check-all
```

## Technical Notes

- **Не трогать** существующий `get_historical` (`/historical/{route_id}`).
- Параметры через `Query(default=None, alias="from")` чтобы `?from=...` работало.
- `period_start < to_date` (не `<=`) чтобы исключить overlap.
- Response класс с `media_type="text/csv; charset=utf-8"`.
