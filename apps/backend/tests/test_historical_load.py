"""Tests for T-218: /api/v1/historical/load (block 'kak bylo')."""

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


def _seed_actuals_two_routes(factory) -> None:
    async def seed() -> None:
        async with factory() as s:
            for route_id, vals in [(1, [40.0, 80.0, 120.0]), (7, [60.0, 90.0, 110.0])]:
                for hour, v in enumerate(vals):
                    s.add(
                        Actual(
                            route_id=route_id,
                            period_start=datetime(2025, 10, 30, hour, 0, 0, tzinfo=UTC),
                            period_end=datetime(
                                2025, 10, 30, hour + 1, 0, 0, tzinfo=UTC
                            ),
                            value=v,
                        )
                    )
            await s.commit()

    asyncio.run(seed())


def test_historical_load_empty_returns_empty_list(client) -> None:
    r = client.get("/api/v1/historical/load")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["loads"] == []
    assert body["count"] == 0
    assert body["source"] == "actuals"
    assert body["used_fallback"] is True


def test_historical_load_returns_avg_per_route(app_with_db, client) -> None:
    _seed_actuals_two_routes(app_with_db.state.session_factory)

    r = client.get(
        "/api/v1/historical/load",
        params={"from": "2025-10-29T00:00:00", "to": "2025-10-31T00:00:00"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    assert body["used_fallback"] is False

    by_route = {item["route_id"]: item for item in body["loads"]}
    # route 1: avg = 80, load_pct = 80/150*100 = 53.33
    assert by_route[1]["boardings_avg"] == pytest.approx(80.0)
    assert by_route[1]["load_pct"] == pytest.approx(53.33, rel=0.01)
    assert by_route[1]["tier"] == "green"
    assert by_route[1]["period_end"] is not None
    assert by_route[1]["sample_size"] == 3


def test_historical_load_no_params_falls_back_to_max_period(
    app_with_db, client
) -> None:
    factory = app_with_db.state.session_factory

    async def seed() -> None:
        async with factory() as s:
            # Data only in 2025-10-30. 'now()' is 2026 → empty window without fallback.
            for hour, v in enumerate([50.0, 75.0, 100.0]):
                s.add(
                    Actual(
                        route_id=1,
                        period_start=datetime(2025, 10, 30, hour, 0, 0, tzinfo=UTC),
                        period_end=datetime(2025, 10, 30, hour + 1, 0, 0, tzinfo=UTC),
                        value=v,
                    )
                )
            await s.commit()

    asyncio.run(seed())

    r = client.get("/api/v1/historical/load")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1
    assert body["used_fallback"] is True
    item = body["loads"][0]
    assert item["route_id"] == 1
    # avg = 75.0
    assert item["boardings_avg"] == pytest.approx(75.0)
    # load_pct = 75/150*100 = 50.0
    assert item["load_pct"] == pytest.approx(50.0, rel=0.01)
    assert item["tier"] == "green"
    # to_date should be MAX(period_start) = 2025-10-30 02:00:00
    assert item["period_end"] is not None
