"""Tests for T-218: /api/v1/predictions/load (block 'kak budet')."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.main import create_app
from app.models import Base, FeatureToggle, Prediction, ZeroOverride


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


def _seed(factory):
    async def seed():
        async with factory() as s:
            s.add(FeatureToggle(name="use_poi", description="POI", enabled=True, is_default=True))
            s.add(FeatureToggle(name="use_weather", description="Wx", enabled=True, is_default=True))
            s.add(FeatureToggle(name="use_events", description="Ev", enabled=True, is_default=True))
            s.add(FeatureToggle(name="use_seasonal", description="Se", enabled=True, is_default=True))
            s.add(FeatureToggle(name="use_traffic", description="Tr", enabled=False, is_default=False))
            s.add(ZeroOverride(name="zero_route_5", description="r5", enabled=True, params={"route_id": 5}))
            s.add(ZeroOverride(name="zero_night_pred_cap", description="night", enabled=True, params={"pred_cap": 55, "hours": [0, 1, 2, 3, 4]}))
            for route_id, vals in [(1, [40.0, 80.0, 120.0]), (7, [60.0, 90.0, 110.0])]:
                for hour, v in enumerate(vals):
                    s.add(Prediction(
                        route_id=route_id,
                        period_start=datetime(2025, 11, 1, hour, 0, 0, tzinfo=UTC),
                        period_end=datetime(2025, 11, 1, hour + 1, 0, 0, tzinfo=UTC),
                        value=v, lower=v * 0.9, upper=v * 1.1,
                        horizon="day", granularity="hour",
                        model_id="baseline_v1", model_kind="baseline", model_version="v0.1.0",
                        feature_set="with_all", zeros_applied=True,
                        coef_weather=1.0, coef_event=1.0, coef_season=1.0,
                    ))
            await s.commit()
    asyncio.run(seed())


def test_predictions_load_empty_returns_empty_list(client) -> None:
    r = client.get("/api/v1/predictions/load")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["loads"] == [] and body["count"] == 0
    assert body["source"] == "predictions"


def test_predictions_load_returns_avg_per_route(app_with_db, client) -> None:
    _seed(app_with_db.state.session_factory)
    r = client.get("/api/v1/predictions/load")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    by_route = {item["route_id"]: item for item in body["loads"]}
    assert set(by_route) == {1, 7}
    assert by_route[1]["boardings_avg"] == pytest.approx(80.0)
    assert by_route[1]["load_pct"] == pytest.approx(53.33, rel=0.01)
    assert by_route[1]["tier"] == "green"


def test_predictions_load_filters_by_date_range(app_with_db, client) -> None:
    _seed(app_with_db.state.session_factory)
    r = client.get(
        "/api/v1/predictions/load",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    # Both routes have data on 2025-11-01, so both present
    assert {item["route_id"] for item in body["loads"]} == {1, 7}
