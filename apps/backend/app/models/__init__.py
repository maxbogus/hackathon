"""SQLAlchemy ORM models for Transit-AI backend.

T-194: схема БД для:
  - Actual (historical boardings, TimescaleDB hypertable)
  - Prediction (ML predictions с feature_set, model_id, zeros_applied)
  - FeatureToggle (per-feature вкл/выкл, defaults)
  - ZeroOverride (zero-strategy toggles: route 5, night hours)
  - PredictionRun (лог запусков ml_pipeline Celery tasks)

Privacy:
  - no-PII: все таблицы содержат только агрегированные данные и метаданные.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""


from app.models.actual import Actual
from app.models.feature_toggle import FeatureToggle
from app.models.prediction import Prediction
from app.models.prediction_run import PredictionRun
from app.models.zero_override import ZeroOverride

__all__ = [
    "Actual",
    "Base",
    "FeatureToggle",
    "Prediction",
    "PredictionRun",
    "ZeroOverride",
]
