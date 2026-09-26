"""Tests for T-195 endpoints: /historical, /features, /predictions/db, /predictions/export.csv.

Используем SQLite in-memory через dependency override (get_db).
Каждый тест создаёт свой engine (clean schema).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.main import create_app
from app.models import Base


@pytest.fixture
def app_with_db():
    """FastAPI app c get_db, возвращающим AsyncSession поверх in-memory sqlite+aiosqlite."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    async def init_schema():
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_schema())

    session_factory = async_sessionmaker(eng, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # Stash session_factory for use in seed fixture
    app.state.session_factory = session_factory

    yield app

    async def dispose():
        await eng.dispose()

    asyncio.run(dispose())


@pytest.fixture
def client(app_with_db):
    return TestClient(app_with_db)


# --- Seed helpers (replicate alembic migration seeds for in-memory tests) ---

SEED_FEATURES = [
    ("use_poi", "POI features (T-168)", True, True),
    ("use_traffic", "Traffic features (T-124)", False, False),
    ("use_weather", "Weather features (T-123)", True, True),
    ("use_events", "Events calendar (T-172)", True, True),
    ("use_seasonal", "Seasonal calendar", True, True),
    ("use_lag", "Lag features (T-152)", True, True),
]

SEED_ZEROS = [
    ("zero_route_5", "Zero out route 5 (F-051)", True, {"route_id": 5}),
    (
        "zero_night_pred_cap",
        "Zero night hours (F-060)",
        True,
        {"pred_cap": 55, "hours": [0, 1, 2, 3, 4]},
    ),
    ("zero_weekend", "Zero weekends (T-180, untested)", False, {"weekday_in": [5, 6]}),
    (
        "zero_holidays",
        "Zero holidays (T-180, untested)",
        False,
        {"holiday_multiplier": 0.0},
    ),
]


@pytest.fixture
def seeded_client(app_with_db):
    """Client + seeded feature_toggles + zero_overrides (replicate T-194 seeds)."""
    from app.models import FeatureToggle, ZeroOverride

    factory = app_with_db.state.session_factory

    async def seed():
        async with factory() as s:
            for name, desc, enabled, is_default in SEED_FEATURES:
                s.add(
                    FeatureToggle(
                        name=name,
                        description=desc,
                        enabled=enabled,
                        is_default=is_default,
                    )
                )
            for name, desc, enabled, params in SEED_ZEROS:
                s.add(
                    ZeroOverride(
                        name=name,
                        description=desc,
                        enabled=enabled,
                        params=params,
                    )
                )
            await s.commit()

    asyncio.run(seed())
    return TestClient(app_with_db)


# ============== /features tests ==============


def test_list_features_returns_seed(seeded_client) -> None:
    r = seeded_client.get("/api/v1/features")
    assert r.status_code == 200
    data = r.json()
    names = [t["name"] for t in data["feature_toggles"]]
    assert "use_poi" in names
    assert "use_traffic" in names
    zero_names = [o["name"] for o in data["zero_overrides"]]
    assert "zero_route_5" in zero_names
    assert "zero_night_pred_cap" in zero_names


def test_toggle_feature(seeded_client) -> None:
    r = seeded_client.post("/api/v1/features/use_poi/toggle", json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False

    r = seeded_client.get("/api/v1/features")
    use_poi = next(t for t in r.json()["feature_toggles"] if t["name"] == "use_poi")
    assert use_poi["enabled"] is False


def test_toggle_nonexistent_feature_returns_404(seeded_client) -> None:
    r = seeded_client.post(
        "/api/v1/features/nonexistent/toggle", json={"enabled": True}
    )
    assert r.status_code == 404


def test_toggle_zero_with_params(seeded_client) -> None:
    r = seeded_client.post(
        "/api/v1/zeros/zero_night_pred_cap/toggle",
        json={"enabled": False, "params": {"pred_cap": 100, "hours": [0, 1, 2]}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False
    assert data["params"]["pred_cap"] == 100


# ============== /historical tests ==============


def test_historical_empty(client) -> None:
    """Empty actuals → empty points list (no error)."""
    r = client.get(
        "/api/v1/historical/7",
        params={"from": "2025-01-01T00:00:00", "to": "2025-12-31T00:00:00"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["route_id"] == 7
    assert data["points"] == []


def test_historical_400_on_bad_range(client) -> None:
    r = client.get(
        "/api/v1/historical/7",
        params={"from": "2025-12-31T00:00:00", "to": "2025-01-01T00:00:00"},
    )
    assert r.status_code == 400


def test_historical_invalid_granularity(client) -> None:
    r = client.get(
        "/api/v1/historical/7",
        params={
            "from": "2025-01-01T00:00:00",
            "to": "2025-01-02T00:00:00",
            "granularity": "minute",
        },
    )
    assert r.status_code == 422


def test_list_routes_with_history_empty(client) -> None:
    r = client.get("/api/v1/historical")
    assert r.status_code == 200
    assert r.json() == {"routes": [], "count": 0}


# ============== /predictions/db tests ==============


def test_predictions_db_empty(client) -> None:
    r = client.get(
        "/api/v1/predictions/db/7",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["route_id"] == 7
    assert data["points"] == []


def test_predictions_db_default_filters(seeded_client) -> None:
    """Default filters из feature_toggles + zero_overrides."""
    r = seeded_client.get(
        "/api/v1/predictions/db/7",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-01T01:00:00"},
    )
    data = r.json()
    assert data["zeros_applied"] is True
    assert data["feature_set"] == "with_all"


# ============== /predictions/export.csv tests ==============


def test_export_csv_empty(client) -> None:
    r = client.get("/api/v1/predictions/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


def test_export_csv_headers(client) -> None:
    r = client.get("/api/v1/predictions/export.csv")
    assert "X-CSV-MD5" in r.headers
    assert "X-Row-Count" in r.headers
    assert "attachment" in r.headers["content-disposition"]


def test_export_csv_with_data(seeded_client, app_with_db) -> None:
    """End-to-end: заполняем БД прогнозами, проверяем CSV формат и headers."""
    from datetime import UTC, datetime

    from app.models import Prediction

    factory = app_with_db.state.session_factory

    async def seed():
        async with factory() as s:
            # 2 routes × 2 hours = 4 predictions
            for r in (7, 11):
                for h in (8, 9):
                    s.add(
                        Prediction(
                            route_id=r,
                            period_start=datetime(2025, 11, 1, h, tzinfo=UTC),
                            period_end=datetime(2025, 11, 1, h + 1, tzinfo=UTC),
                            horizon="day",
                            granularity="hour",
                            value=42.5 + h,
                            lower=30.0,
                            upper=55.0,
                            model_id="xgboost_v_default",
                            model_kind="xgboost",
                            model_version="v1.0.0",
                            feature_set="with_all",  # matches seeded state
                            feature_flags={"use_poi": True},
                            zeros_applied=True,  # matches seeded state
                            zero_config={"pred_cap": 55},
                            coef_weather=1.0,
                            coef_event=1.0,
                            coef_season=1.0,
                        )
                    )
            await s.commit()

    asyncio.run(seed())

    r = seeded_client.get(
        "/api/v1/predictions/export.csv",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    assert r.status_code == 200
    assert r.headers["X-Row-Count"] == "4"
    lines = r.text.strip().split("\n")
    assert len(lines) == 4
    # Формат: route;date;hour;prediction
    # value = 42.5 + h, для h=8 → 50.50
    assert lines[0] == "7;2025-11-01;8;50.50"
    assert lines[2] == "11;2025-11-01;8;50.50"
    # MD5 валиден (32 hex chars)
    assert len(r.headers["X-CSV-MD5"]) == 32


def test_export_csv_filter_zeros_off(seeded_client, app_with_db) -> None:
    """С zeros_applied=False → другой feature_set, другие прогнозы."""
    from datetime import UTC, datetime

    from app.models import Prediction

    factory = app_with_db.state.session_factory

    async def seed():
        async with factory() as s:
            for zeros, fs in [(True, "with_all"), (False, "baseline")]:
                s.add(
                    Prediction(
                        route_id=7,
                        period_start=datetime(2025, 11, 1, 8, tzinfo=UTC),
                        period_end=datetime(2025, 11, 1, 9, tzinfo=UTC),
                        horizon="day",
                        granularity="hour",
                        value=50.0 if zeros else 60.0,
                        model_id="m",
                        model_kind="xgboost",
                        model_version="v1",
                        feature_set=fs,
                        feature_flags={},
                        zeros_applied=zeros,
                        zero_config={},
                        coef_weather=1.0,
                        coef_event=1.0,
                        coef_season=1.0,
                    )
                )
            await s.commit()

    asyncio.run(seed())

    # С zeros_applied=False → 1 prediction
    r = seeded_client.get(
        "/api/v1/predictions/export.csv",
        params={
            "from": "2025-11-01T00:00:00",
            "to": "2025-11-02T00:00:00",
            "zeros_applied": "false",
            "feature_set": "baseline",
        },
    )
    assert r.headers["X-Row-Count"] == "1"
    assert "60.00" in r.text
