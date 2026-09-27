"""Predictions runs API — генерация, кандидат, подмена, эталон (T-230).

Flow (см. clinerule 23/24):
    POST /predictions/regenerate      → Celery ml_pipeline.predict_window
    GET  /predictions/runs/{id}       → статус; при SUCCESS — метаданные кандидата
                                        + recommendation (clinerule 24 R3)
    POST /predictions/runs/{id}/ingest→ загрузить CSV кандидата в БД
    POST /predictions/runs/{id}/reject→ «оставить эталон»
    POST /predictions/restore-etalon  → вернуть эталон активным
    GET  /predictions/active          → параметры активного набора

Ключевое: backend НЕ подменяет набор автоматически — он предлагает кандидата,
решение принимает пользователь в UI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pipeline import _get_celery_app
from app.config import settings
from app.db import get_db
from app.models import PredictionRun
from app.predictions_active import (
    active_params,
    build_recommendation,
    feature_state,
    ingest_candidate,
    restore_etalon,
    validate_candidate,
)
from app.predictions_csv import find_manifest_for_submission, read_manifest
from app.schemas.predictions_runs import (
    ActiveSetResponse,
    PredictionRunListResponse,
    PredictionRunOut,
    RegenerateRequest,
)

router = APIRouter(prefix="/api/v1", tags=["predictions-runs"])

_CELERY_TASK = "ml_pipeline.predict_window"
_RUNNING = {"running", "queued", "started"}
_TERMINAL = {"ready", "loaded", "rejected", "failed"}


class IngestBody(BaseModel):
    """Тело POST /predictions/runs/{id}/ingest."""

    activate: bool = True


class RunActionResponse(BaseModel):
    """Ответ на ingest/reject/restore."""

    run: PredictionRunOut | None = None
    rows: int = 0
    active_submission_id: str | None = None
    message: str = ""


def _new_submission_id() -> str:
    """Уникальный submission_id для UI-прогона (clinerule 23 R1/R5)."""
    return "ui-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


async def _to_out(session: AsyncSession, run: PredictionRun) -> PredictionRunOut:
    """ORM → schema + вычисленный is_active (по активному submission_id)."""
    active = await active_params(session)
    out = PredictionRunOut.model_validate(run)
    out.is_active = bool(
        active is not None and run.submission_id == active.submission_id
    )
    if run.csv_path:
        out.csv_filename = run.csv_path.replace("\\", "/").rsplit("/", 1)[-1]
    return out


@router.post("/predictions/regenerate", summary="T-230: сгенерировать новый набор")
async def regenerate(
    body: RegenerateRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Запускает Celery-генерацию прогнозов с параметрами из UI/БД."""
    state = await feature_state(session)
    submission_id = _new_submission_id()
    feature_set = body.feature_set or state.feature_set
    zeros_applied = (
        state.zeros_applied if body.zeros_applied is None else body.zeros_applied
    )
    start_date = body.start_date or settings.submission_period_start
    end_date = body.end_date or settings.submission_period_end
    model_id = body.model_id or f"xgboost_v_ui_{datetime.now(UTC):%Y%m%d%H%M}"

    kwargs: dict[str, Any] = {
        "model_id": model_id,
        "start_date": start_date,
        "end_date": end_date,
        "submission_id": submission_id,
        "coef_weather": body.coef_weather,
        "coef_event": body.coef_event,
        "coef_season": body.coef_season,
        "zeros": zeros_applied,
        "feature_flags": dict(state.feature_flags),
        "zero_overrides": dict(state.zero_config),
        "model_kind": body.model_kind,
    }

    try:
        celery_app = _get_celery_app()
        result = celery_app.send_task(_CELERY_TASK, kwargs=kwargs)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Celery недоступен: {exc}. Подними worker: make pipeline-up",
        ) from exc

    run = PredictionRun(
        celery_task_id=result.id,
        task_name=_CELERY_TASK,
        status="running",
        submission_id=submission_id,
        model_id=model_id,
        feature_set=feature_set,
        pipeline_kind="predict",
        params={
            "feature_set": feature_set,
            "zeros_applied": zeros_applied,
            "feature_flags": dict(state.feature_flags),
            "zero_config": dict(state.zero_config),
            "coef_weather": body.coef_weather,
            "coef_event": body.coef_event,
            "coef_season": body.coef_season,
            "start_date": start_date,
            "end_date": end_date,
            "model_kind": body.model_kind,
        },
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return {
        "run_id": run.id,
        "task_id": result.id,
        "status": run.status,
        "submission_id": submission_id,
    }


@router.get(
    "/predictions/runs",
    response_model=PredictionRunListResponse,
    summary="T-230: список запусков генерации",
)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> PredictionRunListResponse:
    """Последние запуски (новые сверху) + какой submission_id активен."""
    rows = (
        (
            await session.execute(
                select(PredictionRun).order_by(PredictionRun.id.desc()).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    active = await active_params(session)
    out = [await _to_out(session, r) for r in rows]
    return PredictionRunListResponse(
        runs=out,
        count=len(out),
        active_submission_id=active.submission_id if active else None,
    )


async def _active_holdout(session: AsyncSession) -> float | None:
    """Holdout активного набора (для вердикта clinerule 24 R3)."""
    active = await active_params(session)
    if active is None or active.submission_id is None:
        return None
    return await session.scalar(
        select(PredictionRun.holdout_wape_score)
        .where(PredictionRun.submission_id == active.submission_id)
        .order_by(PredictionRun.id.desc())
        .limit(1)
    )


def _celery_status(task_id: str) -> tuple[str | None, Any]:
    """(status, info) из Celery; (None, None) если broker недоступен."""
    try:
        res = _get_celery_app().AsyncResult(task_id)
        return res.status, (res.result if res.ready() else None)
    except Exception:  # noqa: BLE001 — Celery/Redis best-effort
        return None, None


async def _mark_candidate_ready(session: AsyncSession, run: PredictionRun) -> None:
    """Найти CSV+manifest кандидата и заполнить метаданные (ещё НЕ в БД)."""
    manifest_path = find_manifest_for_submission(
        settings.predictions_dir, run.submission_id or ""
    )
    if manifest_path is None:
        run.status = "failed"
        run.error = "manifest не найден в predictions/ (worker не дописал?)"
        await session.commit()
        return

    manifest = read_manifest(manifest_path) or {}
    csv_name = str(manifest.get("csv_filename") or "")
    csv_path = settings.predictions_dir / csv_name
    check = validate_candidate(csv_path, manifest_path)

    run.manifest_path = str(manifest_path)
    run.csv_path = str(csv_path)
    run.row_count = check.row_count or None
    run.holdout_wape_score = check.holdout_wape_score
    if not check.ok:
        run.status = "ready" if "NEEDS_FIX" in check.reason else "failed"
        run.error = check.reason
        run.recommendation = "NEEDS_FIX"
    else:
        run.status = "ready"
        run.error = None
        run.recommendation = build_recommendation(
            check.holdout_wape_score, await _active_holdout(session)
        )
    await session.commit()


@router.get(
    "/predictions/runs/{run_id}",
    response_model=PredictionRunOut,
    summary="T-230: статус запуска + кандидат (при Celery SUCCESS)",
)
async def get_run(
    run_id: int,
    session: AsyncSession = Depends(get_db),
) -> PredictionRunOut:
    """Статус запуска. Пока Celery работает — опрашиваем; при SUCCESS ищем CSV."""
    run = await session.get(PredictionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")

    if run.status in _RUNNING and not run.is_etalon:
        status, info = _celery_status(run.celery_task_id)
        if status == "SUCCESS":
            await _mark_candidate_ready(session, run)
        elif status == "FAILURE":
            run.status = "failed"
            run.error = str(info)[:500]
            await session.commit()
        elif status is not None:
            run.status = "running"
            await session.commit()

    await session.refresh(run)
    return await _to_out(session, run)


@router.post(
    "/predictions/runs/{run_id}/ingest",
    response_model=RunActionResponse,
    summary="T-230: загрузить CSV кандидата в БД (и опционально активировать)",
)
async def ingest_run(
    run_id: int,
    body: IngestBody,
    session: AsyncSession = Depends(get_db),
) -> RunActionResponse:
    """INSERT кандидата в `predictions`. Идемпотентность: повторный ingest → 409."""
    run = await session.get(PredictionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    if run.status == "loaded":
        raise HTTPException(status_code=409, detail="run already loaded")
    if run.status not in {"ready"}:
        raise HTTPException(
            status_code=409,
            detail=f"run status={run.status!r}, ожидался 'ready' (сначала поллинг)",
        )

    check = await ingest_candidate(session, run, activate_after=body.activate)
    if not check.ok:
        raise HTTPException(status_code=422, detail=check.reason)
    await session.refresh(run)
    active = await active_params(session)
    return RunActionResponse(
        run=await _to_out(session, run),
        rows=check.row_count,
        active_submission_id=active.submission_id if active else None,
        message=check.reason,
    )


@router.post(
    "/predictions/runs/{run_id}/reject",
    response_model=RunActionResponse,
    summary="T-230: отклонить кандидата (оставить эталон/текущий набор)",
)
async def reject_run(
    run_id: int,
    session: AsyncSession = Depends(get_db),
) -> RunActionResponse:
    """Помечает кандидата `rejected`. Активный набор НЕ меняется."""
    run = await session.get(PredictionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {run_id} not found")
    if run.status == "loaded":
        raise HTTPException(
            status_code=409, detail="run already loaded — нельзя отклонить"
        )
    run.status = "rejected"
    await session.commit()
    await session.refresh(run)
    active = await active_params(session)
    return RunActionResponse(
        run=await _to_out(session, run),
        rows=0,
        active_submission_id=active.submission_id if active else None,
        message="Кандидат отклонён, активный набор не изменён",
    )


@router.post(
    "/predictions/restore-etalon",
    response_model=RunActionResponse,
    summary="T-230: вернуть эталонный набор как активный",
)
async def restore_etalon_endpoint(
    session: AsyncSession = Depends(get_db),
) -> RunActionResponse:
    """`UPDATE predictions SET is_active = is_etalon` (строки не удаляются)."""
    try:
        rows = await restore_etalon(session)
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    active = await active_params(session)
    return RunActionResponse(
        rows=rows,
        active_submission_id=active.submission_id if active else None,
        message="Эталонный набор снова активен",
    )


@router.get(
    "/predictions/active",
    response_model=ActiveSetResponse,
    summary="T-230: параметры активного набора (source of truth для UI)",
)
async def get_active_set(
    session: AsyncSession = Depends(get_db),
) -> ActiveSetResponse:
    """Что сейчас отдают чтения: submission_id, модель, фичи, zeros, coefs, строк."""
    active = await active_params(session)
    if active is None:
        return ActiveSetResponse()
    is_etalon = bool(
        await session.scalar(
            select(PredictionRun.is_etalon)
            .where(PredictionRun.submission_id == active.submission_id)
            .limit(1)
        )
    )
    return ActiveSetResponse(
        submission_id=active.submission_id,
        model_id=active.model_id,
        feature_set=active.feature_set,
        zeros_applied=active.zeros_applied,
        coef_weather=active.coef_weather,
        coef_event=active.coef_event,
        coef_season=active.coef_season,
        row_count=active.row_count,
        is_etalon=is_etalon,
    )


__all__ = [
    "IngestBody",
    "RunActionResponse",
    "get_active_set",
    "get_run",
    "ingest_run",
    "list_runs",
    "regenerate",
    "reject_run",
    "restore_etalon_endpoint",
    "router",
]
