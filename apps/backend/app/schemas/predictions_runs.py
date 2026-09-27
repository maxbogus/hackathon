"""Schemas для генерации/подмены наборов прогнозов (T-230).

Контракт дашборда «Аналитик»:
  POST /api/v1/predictions/regenerate        → запустить Celery-генерацию
  GET  /api/v1/predictions/runs              → список запусков + какой активен
  GET  /api/v1/predictions/runs/{id}         → статус кандидата
  POST /api/v1/predictions/runs/{id}/ingest  → загрузить CSV кандидата в БД
  POST /api/v1/predictions/runs/{id}/reject  → «оставить эталон»
  POST /api/v1/predictions/restore-etalon    → вернуть эталон активным
  GET  /api/v1/predictions/active            → параметры активного набора
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

__all__ = [
    "ActiveSetResponse",
    "PredictionRunListResponse",
    "PredictionRunOut",
    "RegenerateRequest",
]


class RegenerateRequest(BaseModel):
    """Параметры генерации нового набора прогнозов.

    Всё опционально: не заданные поля берутся из БД (feature_toggles /
    zero_overrides) и из `settings` (submission period).
    """

    coef_weather: float = Field(default=1.0, ge=0, le=3)
    coef_event: float = Field(default=1.0, ge=0, le=3)
    coef_season: float = Field(default=1.0, ge=0, le=3)
    start_date: str | None = Field(default=None, description="YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD")
    model_id: str | None = None
    model_kind: str = Field(
        default="xgboost_route", pattern="^(route_baseline|xgboost_route)$"
    )
    feature_set: str | None = Field(
        default=None, description="Если None — выводится из feature_toggles"
    )
    zeros_applied: bool | None = Field(
        default=None, description="Если None — выводится из zero_overrides"
    )


class PredictionRunOut(BaseModel):
    """Один запуск генерации (candidate lifecycle)."""

    id: int
    celery_task_id: str
    status: str
    submission_id: str | None = None
    model_id: str | None = None
    feature_set: str | None = None
    pipeline_kind: str | None = None
    row_count: int | None = None
    holdout_wape_score: float | None = None
    recommendation: str | None = None
    error: str | None = None
    is_etalon: bool = False
    is_active: bool = False
    csv_filename: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    activated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PredictionRunListResponse(BaseModel):
    """Список запусков + текущий активный набор."""

    runs: list[PredictionRunOut]
    count: int
    active_submission_id: str | None = None


class ActiveSetResponse(BaseModel):
    """Параметры активного набора (source of truth для UI-подписи)."""

    submission_id: str | None = None
    model_id: str | None = None
    feature_set: str | None = None
    zeros_applied: bool | None = None
    coef_weather: float = 1.0
    coef_event: float = 1.0
    coef_season: float = 1.0
    row_count: int = 0
    is_etalon: bool = False
