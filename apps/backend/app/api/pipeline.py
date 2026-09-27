"""POST /api/v1/pipeline/full + GET /api/v1/pipeline/status/{task_id} (T-198).

Позволяет UI кнопке "Run now" запустить Celery task ml_pipeline.full_pipeline
и polling-ом получить результат.

Architecture:
  UI → POST /pipeline/full → celery_app.send_task("ml_pipeline.full_pipeline")
                          → response {task_id, status: "queued"}
  UI → poll GET /pipeline/status/{task_id} каждые 3 сек
    → celery_app.AsyncResult(task_id).status

T-198k: lazy import celery (он не установлен в backend wheels — только в
harvester/ml-pipeline). Backend использует celery как HTTP-клиент, но импорт
отложен до первого вызова endpoint.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["pipeline"])


class PipelineFullBody(BaseModel):
    """T-230: параметры генерации для POST /pipeline/full (все опциональны)."""

    submission_id: str | None = None
    coef_weather: float = 1.0
    coef_event: float = 1.0
    coef_season: float = 1.0
    zeros: bool = False


@lru_cache(maxsize=1)
def _get_celery_app():
    """Lazy Celery client (НЕ worker — только клиент для send_task/AsyncResult)."""
    from celery import Celery

    # Broker = db 1, Backend = db 2 (как у harvester/ml-pipeline workers).
    return Celery(
        "transit-ai-backend-client",
        broker="redis://redis:6379/1",
        backend="redis://redis:6379/2",
    )


@router.post(
    "/pipeline/full", summary="Trigger ml_pipeline.full_pipeline (T-198/T-230)"
)
async def trigger_pipeline_full(body: PipelineFullBody | None = None) -> dict[str, str]:
    """Запускает Celery task full_pipeline (train + predict) с параметрами."""
    kwargs = body.model_dump(exclude_none=True) if body is not None else {}
    celery_app = _get_celery_app()
    result = celery_app.send_task("ml_pipeline.full_pipeline", kwargs=kwargs)
    return {"task_id": result.id, "status": "queued"}


@router.get(
    "/pipeline/status/{task_id}",
    summary="Get Celery task status (T-198)",
)
async def get_pipeline_status(task_id: str) -> dict[str, object]:
    """Возвращает текущий статус Celery task."""
    celery_app = _get_celery_app()
    res = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None,
    }


__all__ = [
    "PipelineFullBody",
    "get_pipeline_status",
    "router",
    "trigger_pipeline_full",
]
