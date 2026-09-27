"""Prediction ORM model.

T-194: хранит результаты инференса (ML + калибровки) с метаданными
о фичах и применённых zero-overrides. Позволяет фронту фильтровать
прогнозы по model_id / feature_set / zeros_applied.

Privacy: no-PII (агрегированный пассажиропоток + метаданные).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Prediction(Base):
    """One prediction point: route × datetime → value."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    horizon: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # day | month | year
    granularity: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # hour | day | month

    value: Mapped[float] = mapped_column(Float, nullable=False)
    lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Метаданные модели
    model_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_kind: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # baseline|xgboost|gru|hybrid
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)  # vN.M.K

    # Конфигурация применённая при инференсе
    feature_set: Mapped[str] = mapped_column(
        String(64), nullable=False, default="baseline"
    )
    """baseline | with_poi | with_traffic | with_weather | all — для фильтрации фронтом."""
    feature_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    """per-feature включены/выключены: {use_poi: True, use_traffic: False, ...}"""
    zeros_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """Применялась ли zero-strategy (route 5, night hours)."""
    zero_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    """{zero_route_5: True, zero_night_pred_cap: 55, ...}"""

    # Корректирующие коэффициенты (clinerule 24)
    coef_weather: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    coef_event: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    coef_season: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Submission lineage
    submission_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    git_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # T-230: active/etalon switching.
    # Строки НИКОГДА не удаляются: «подмена набора» = атомарный UPDATE флага.
    # is_etalon — эталонный набор (restore-etalon возвращает его как активный).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_etalon: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_predictions_route_period", "route_id", "period_start"),
        Index("ix_predictions_model_feature", "model_id", "feature_set"),
        Index("ix_predictions_submission", "submission_id"),
        Index("ix_predictions_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction route={self.route_id} t={self.period_start.isoformat()} "
            f"value={self.value:.2f} model={self.model_id} fs={self.feature_set} zeros={self.zeros_applied}>"
        )
