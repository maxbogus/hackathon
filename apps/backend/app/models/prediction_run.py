"""PredictionRun ORM model — лог запусков ml_pipeline Celery tasks.

T-194: позволяет восстановить lineage любого prediction (когда, какая модель,
какие параметры, holdout_wape_score, manifest_path).

Privacy: no-PII.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PredictionRun(Base):
    """Один запуск ml_pipeline Celery task."""

    __tablename__ = "prediction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    celery_task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    task_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    """ml_pipeline.train_xgboost | ml_pipeline.predict_window | ml_pipeline.full_pipeline"""
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    """started | success | failure | revoked"""
    submission_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feature_set: Mapped[str | None] = mapped_column(String(64), nullable=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    """kwargs, переданные в задачу"""
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """stdout_tail, returncode, ошибки"""
    holdout_wape_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manifest_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    csv_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<PredictionRun {self.task_name} status={self.status} "
            f"model={self.model_id} submission={self.submission_id}>"
        )
