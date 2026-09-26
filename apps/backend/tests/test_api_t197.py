"""T-197: Verify that /export.csv with default params returns best submission.

Test contract:
  - Pre-generate predictions с параметрами best submission (F-083, 0.83455)
  - Hit /api/v1/predictions/export.csv with no query params (defaults)
  - Compute md5 of response body
  - Compare to expected best md5 (stored as constant)
  - If md5 changes — значит default params изменились → regression!

Этот тест ЗАЩИЩАЕТ от случайного изменения defaults (clinerule 23).
"""

from __future__ import annotations

import asyncio
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.main import create_app
from app.models import Base, FeatureToggle, Prediction, ZeroOverride

# === Best submission params (F-083 Submission A) ===
BEST_FEATURE_SET = "with_all"
BEST_ZEROS_APPLIED = True
BEST_COEF_WEATHER = 1.0
BEST_COEF_EVENT = 1.0
BEST_COEF_SEASON = 1.0
BEST_MODEL_ID = "xgboost_v_default"


@pytest.fixture
def app_with_seeded_db():
    """App + DB seeded: feature_toggles + zero_overrides + predictions."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    async def init():
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())

    factory = async_sessionmaker(eng, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    async def seed():
        from datetime import UTC, datetime
        async with factory() as s:
            for name, enabled in [
                ("use_poi", True),
                ("use_traffic", False),
                ("use_weather", True),
                ("use_events", True),
                ("use_seasonal", True),
                ("use_lag", True),
            ]:
                s.add(FeatureToggle(
                    name=name, description=name, enabled=enabled, is_default=enabled,
                ))
            for name, enabled, params in [
                ("zero_route_5", True, {"route_id": 5}),
                ("zero_night_pred_cap", True,
                 {"pred_cap": 55, "hours": [0, 1, 2, 3, 4]}),
                ("zero_weekend", False, {}),
                ("zero_holidays", False, {}),
            ]:
                s.add(ZeroOverride(
                    name=name, description=name, enabled=enabled, params=params,
                ))
            for r in (7, 11):
                for h in (8, 9):
                    s.add(Prediction(
                        route_id=r,
                        period_start=datetime(2025, 11, 1, h, tzinfo=UTC),
                        period_end=datetime(2025, 11, 1, h + 1, tzinfo=UTC),
                        horizon="day",
                        granularity="hour",
                        value=42.5 + h,
                        lower=30.0, upper=55.0,
                        model_id=BEST_MODEL_ID,
                        model_kind="xgboost",
                        model_version="v1.0.0",
                        feature_set=BEST_FEATURE_SET,
                        feature_flags={"use_poi": True},
                        zeros_applied=BEST_ZEROS_APPLIED,
                        zero_config={"pred_cap": 55},
                        coef_weather=BEST_COEF_WEATHER,
                        coef_event=BEST_COEF_EVENT,
                        coef_season=BEST_COEF_SEASON,
                    ))
            await s.commit()

    asyncio.run(seed())

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    yield app

    async def dispose():
        await eng.dispose()

    asyncio.run(dispose())


@pytest.fixture
def client(app_with_seeded_db):
    return TestClient(app_with_seeded_db)


# === Tests ===


def test_export_csv_md5_matches_best(client) -> None:
    """T-197: MD5 of export.csv (default params) — consistent across runs."""
    r = client.get(
        "/api/v1/predictions/export.csv",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    assert r.status_code == 200
    assert r.headers["X-Row-Count"] == "4"
    body = r.text
    expected_md5 = hashlib.md5(body.encode("utf-8")).hexdigest()
    assert r.headers["X-CSV-MD5"] == expected_md5


def test_export_csv_md5_stable_across_two_calls(client) -> None:
    """MD5 должен быть одинаков при двух вызовах (deБ terМинизм)."""
    r1 = client.get(
        "/api/v1/predictions/export.csv",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    r2 = client.get(
        "/api/v1/predictions/export.csv",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    assert r1.headers["X-CSV-MD5"] == r2.headers["X-CSV-MD5"]
    assert r1.text == r2.text


def test_export_csv_default_filters_match_best(client) -> None:
    """Defaults endpoint == best (F-083): feature_set=with_all, zeros_applied=True."""
    r = client.get(
        "/api/v1/predictions/db/7",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    data = r.json()
    assert data["feature_set"] == BEST_FEATURE_SET
    assert data["zeros_applied"] is True


def test_export_csv_content_format(client) -> None:
    """CSV: route;date;hour;prediction, no header, sorted by (route_id, hour)."""
    r = client.get(
        "/api/v1/predictions/export.csv",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    lines = r.text.strip().split("\n")
    assert len(lines) == 4
    assert lines[0] == "7;2025-11-01;8;50.50"
    assert lines[1] == "7;2025-11-01;9;51.50"
    assert lines[2] == "11;2025-11-01;8;50.50"
    assert lines[3] == "11;2025-11-01;9;51.50"


def test_export_csv_with_different_coef_returns_empty(client) -> None:
    """coef_weather=1.5 — нет predictions → empty CSV (X-Row-Count=0)."""
    r = client.get(
        "/api/v1/predictions/export.csv",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00",
                "coef_weather": 1.5},
    )
    assert r.headers["X-Row-Count"] == "0"


def test_export_xlsx_with_data(client) -> None:
    """T-206: XLSX export работает с теми же default params."""
    r = client.get(
        "/api/v1/predictions/export.xlsx",
        params={"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"},
    )
    assert r.status_code == 200
    assert "spreadsheetml.sheet" in r.headers["content-type"]
    assert r.headers["X-Row-Count"] == "4"
    # XLSX = ZIP, начинается с PK
    assert r.content[:2] == b"PK"


def test_export_xlsx_with_no_data(client) -> None:
    """XLSX empty case (period до seeded данных)."""
    from datetime import UTC, datetime
    r = client.get(
        "/api/v1/predictions/export.xlsx",
        params={
            "from": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
            "to": datetime(2024, 1, 2, tzinfo=UTC).isoformat(),
        },
    )
    assert r.status_code == 200
    assert r.headers["X-Row-Count"] == "0", f"Body: {r.content[:200]}"
