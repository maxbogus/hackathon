"""GET /api/v1/predictions/status (T-198).

Возвращает информацию о состоянии predictions в БД:
  - has_predictions: bool — есть ли вообще predictions
  - predictions_count: int — сколько строк
  - actuals_count: int — сколько historical rows (train data)
  - model_ids: list[str] — уникальные model_id в БД
  - running_pipeline: bool — есть ли активные Celery tasks

UI использует:
  - EmptyPredictions component показывается если !has_predictions && !running_pipeline
  - Spinner "Training..." показывается если running_pipeline

Endpoint НЕ требует авторизации (это demo стенд).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models import Actual, Prediction

router = APIRouter(prefix="/api/v1", tags=["predictions-status"])


async def _get_redis() -> AsyncIterator[aioredis.Redis]:
    """FastAPI Depends: aioredis клиент (best-effort, None если Redis недоступен)."""
    client = aioredis.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )
    try:
        yield client
    finally:
        await client.aclose()


@router.get("/predictions/status", summary="Predictions DB status (T-198)")
async def get_status(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(_get_redis)],
) -> dict[str, object]:
    """Возвращает dict с has_predictions, count, model_ids, running_pipeline.

    Используется UI чтобы решить: показывать EmptyPredictions или графики.

    Пример:
        GET /api/v1/predictions/status
        → {"has_predictions": true, "predictions_count": 14640, ...}
    """
    # Counts
    pred_count = (
        await session.execute(select(func.count(Prediction.id)))
    ).scalar() or 0
    actual_count = (await session.execute(select(func.count(Actual.id)))).scalar() or 0

    # Unique model_ids
    model_ids = (
        (await session.execute(select(distinct(Prediction.model_id)))).scalars().all()
    )

    # Active Celery tasks (best-effort)
    running = False
    try:
        # Celery хранит meta в ключах celery-task-meta-* (1 час TTL)
        keys = await redis.keys("celery-task-meta-*")
        running = len(keys) > 0
    except Exception:  # noqa: BLE001 — Redis может быть недоступен, это best-effort
        running = False

    return {
        "has_predictions": pred_count > 0,
        "predictions_count": int(pred_count),
        "actuals_count": int(actual_count),
        "model_ids": sorted(model_ids),
        "running_pipeline": running,
    }


__all__ = ["get_status", "router"]
