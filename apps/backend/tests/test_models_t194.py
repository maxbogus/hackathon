"""Tests for ORM models (T-194).

Проверяем:
  - Все модели импортируются
  - Base.metadata содержит ожидаемые таблицы
  - Каждая модель создаётся с правильными полями (smoke)

Используем sqlite in-memory — TimescaleDB-specific вещи (hypertable)
тестируются отдельно через реальный postgres (clinerule 18).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Actual,
    Base,
    FeatureToggle,
    Prediction,
    PredictionRun,
    ZeroOverride,
)


@pytest.fixture
def engine():
    """In-memory sqlite engine for smoke testing."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def test_all_models_registered() -> None:
    """Все 5 моделей зарегистрированы в Base.metadata."""
    tables = set(Base.metadata.tables.keys())
    assert "actuals" in tables
    assert "predictions" in tables
    assert "feature_toggles" in tables
    assert "zero_overrides" in tables
    assert "prediction_runs" in tables


def test_actual_create(engine) -> None:
    with Session(engine) as session:
        a = Actual(
            route_id=7,
            period_start=datetime(2025, 11, 1, 8, 0, tzinfo=UTC),
            period_end=datetime(2025, 11, 1, 9, 0, tzinfo=UTC),
            value=42.5,
        )
        session.add(a)
        session.commit()
        assert a.id is not None


def test_prediction_full_fields(engine) -> None:
    """Prediction должна принимать ВСЕ поля: feature_set, zeros_applied, coefs, manifest."""
    with Session(engine) as session:
        p = Prediction(
            route_id=7,
            period_start=datetime(2025, 11, 1, 8, 0, tzinfo=UTC),
            period_end=datetime(2025, 11, 1, 9, 0, tzinfo=UTC),
            horizon="day",
            granularity="hour",
            value=42.5,
            lower=30.0,
            upper=55.0,
            model_id="xgboost_v_poi",
            model_kind="xgboost",
            model_version="v1.0.0",
            feature_set="with_poi",
            feature_flags={"use_poi": True, "use_traffic": False},
            zeros_applied=True,
            zero_config={"pred_cap": 55, "hours": [0, 1, 2, 3, 4]},
            coef_weather=1.0,
            coef_event=1.05,
            coef_season=0.95,
            submission_id="test_sub_1",
            git_commit="abc1234",
        )
        session.add(p)
        session.commit()
        assert p.id is not None
        assert p.feature_set == "with_poi"
        assert p.zeros_applied is True


def test_feature_toggle_unique_name(engine) -> None:
    with Session(engine) as session:
        session.add(FeatureToggle(name="use_poi", description="POI", enabled=True))
        session.commit()
        # Second with same name должен упасть (unique constraint)
        with pytest.raises(IntegrityError):
            session.add(FeatureToggle(name="use_poi", description="dup"))
            session.commit()


def test_zero_override_params_json(engine) -> None:
    """ZeroOverride.params хранит JSON конфиг (pred_cap, hours, route_id)."""
    with Session(engine) as session:
        z = ZeroOverride(
            name="zero_night_pred_cap",
            description="night hours",
            enabled=True,
            params={"pred_cap": 55, "hours": [0, 1, 2, 3, 4]},
        )
        session.add(z)
        session.commit()
        assert z.params["pred_cap"] == 55
        assert z.params["hours"] == [0, 1, 2, 3, 4]


def test_prediction_run_lineage(engine) -> None:
    """PredictionRun хранит celery_task_id + manifest_path + csv_path."""
    with Session(engine) as session:
        run = PredictionRun(
            celery_task_id="celery-abc-123",
            task_name="ml_pipeline.predict_window",
            status="success",
            submission_id="v8-poi",
            model_id="xgboost_v_poi",
            feature_set="with_poi",
            params={"coef_weather": 1.0},
            result={"rows": 14640},
            holdout_wape_score=0.8751,
            manifest_path="/app/predictions/submission_xgboost_v_poi_*.json",
            csv_path="/app/predictions/submission_xgboost_v_poi_*.csv",
        )
        session.add(run)
        session.commit()
        assert run.id is not None
        assert run.holdout_wape_score == pytest.approx(0.8751)


def test_prediction_route_period_index() -> None:
    """Проверяем что индекс ix_predictions_route_period определён."""
    table = Base.metadata.tables["predictions"]
    indexes = {idx.name for idx in table.indexes}
    assert "ix_predictions_route_period" in indexes
    assert "ix_predictions_model_feature" in indexes
    assert "ix_predictions_submission" in indexes


def test_all_models_have_repr() -> None:
    """Каждая модель имеет __repr__ для debugging."""
    a = Actual(
        route_id=1,
        period_start=datetime(2025, 1, 1, tzinfo=UTC),
        period_end=datetime(2025, 1, 1, 1, tzinfo=UTC),
        value=10.0,
    )
    assert "Actual" in repr(a)

    z = ZeroOverride(name="test", description="d", enabled=True, params={})
    assert "ZeroOverride" in repr(z)
