"""Tests for T-220: /api/v1/historical/export.csv endpoint."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.main import create_app
from app.models import Actual, Base


@pytest.fixture
def app_with_db():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    async def init_schema() -> None:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_schema())
    session_factory = async_sessionmaker(eng, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.state.session_factory = session_factory
    yield app

    async def dispose() -> None:
        await eng.dispose()

    asyncio.run(dispose())


@pytest.fixture
def client(app_with_db):
    return TestClient(app_with_db)


def _seed_actuals(factory, rows: list[Actual]) -> None:
    async def seed() -> None:
        async with factory() as s:
            for r in rows:
                s.add(r)
            await s.commit()

    asyncio.run(seed())


class TestHistoricalExportCsv:
    """T-220: /api/v1/historical/export.csv endpoint."""

    def test_returns_header_only_when_empty(self, client: TestClient) -> None:
        r = client.get("/api/v1/historical/export.csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert r.text.strip() == "route;date;hour;value"

    def test_returns_seeded_rows(self, client: TestClient, app_with_db) -> None:
        rows = [
            Actual(
                route_id=17,
                period_start=datetime(2025, 10, 29, 10, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 29, 11, 0, tzinfo=UTC),
                value=100.0,
            ),
            Actual(
                route_id=17,
                period_start=datetime(2025, 10, 30, 11, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 30, 12, 0, tzinfo=UTC),
                value=200.0,
            ),
            Actual(
                route_id=17,
                period_start=datetime(2025, 10, 31, 12, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 31, 13, 0, tzinfo=UTC),
                value=300.0,
            ),
        ]
        _seed_actuals(app_with_db.state.session_factory, rows)

        r = client.get("/api/v1/historical/export.csv")
        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        assert lines[0] == "route;date;hour;value"
        assert len(lines) == 4
        # ordering by route_id, period_start
        assert lines[1] == "17;2025-10-29;10;100.00"
        assert lines[2] == "17;2025-10-30;11;200.00"
        assert lines[3] == "17;2025-10-31;12;300.00"

    def test_respects_date_filter(self, client: TestClient, app_with_db) -> None:
        rows = [
            Actual(
                route_id=1,
                period_start=datetime(2025, 10, 29, 10, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 29, 11, 0, tzinfo=UTC),
                value=100.0,
            ),
            Actual(
                route_id=1,
                period_start=datetime(2025, 10, 30, 10, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 30, 11, 0, tzinfo=UTC),
                value=200.0,
            ),
            Actual(
                route_id=1,
                period_start=datetime(2025, 10, 31, 10, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 31, 11, 0, tzinfo=UTC),
                value=300.0,
            ),
        ]
        _seed_actuals(app_with_db.state.session_factory, rows)

        r = client.get(
            "/api/v1/historical/export.csv",
            params={"from": "2025-10-30", "to": "2025-10-31"},
        )
        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        # header + 1 row (только 2025-10-30)
        assert len(lines) == 2
        assert lines[1] == "1;2025-10-30;10;200.00"

    def test_returns_multiple_routes_sorted(
        self, client: TestClient, app_with_db
    ) -> None:
        rows = [
            Actual(
                route_id=7,
                period_start=datetime(2025, 10, 30, 10, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 30, 11, 0, tzinfo=UTC),
                value=50.0,
            ),
            Actual(
                route_id=1,
                period_start=datetime(2025, 10, 30, 10, 0, tzinfo=UTC),
                period_end=datetime(2025, 10, 30, 11, 0, tzinfo=UTC),
                value=20.0,
            ),
        ]
        _seed_actuals(app_with_db.state.session_factory, rows)

        r = client.get("/api/v1/historical/export.csv")
        lines = r.text.strip().split("\n")
        # ORDER BY route_id, period_start → route 1 first
        assert lines[1].startswith("1;")
        assert lines[2].startswith("7;")
