"""Активный набор прогнозов: подмена, эталон, ingest кандидата (T-230).

Проблема, которую решает модуль: в `predictions` может лежать несколько наборов
(эталон + сгенерированные). Без явного признака «активного» набора любое чтение
вернуло бы дубли строк на каждый timestamp.

Инварианты:
  - строки в БД НИКОГДА не удаляются → «подмена» = атомарный UPDATE флага;
  - ровно один активный набор (по `submission_id`);
  - эталон (`is_etalon=true`) доступен для отката в любой момент.

Lifecycle кандидата (`prediction_runs.status`):
    running → ready → loaded | rejected        (+ failed)

См. clinerule 23 (submission versioning), clinerule 24 (recommendation),
clinerule 27 (WAPE-score: больше = лучше).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import FeatureToggle, Prediction, PredictionRun, ZeroOverride
from app.predictions_csv import load_predictions_csv, read_manifest

logger = logging.getLogger(__name__)

__all__ = [
    "ETALON_SUBMISSION_ID",
    "SIGNIFICANT_DELTA",
    "ActiveParams",
    "CandidateCheck",
    "FeatureState",
    "PredictionRecommendation",
    "activate",
    "active_params",
    "build_recommendation",
    "feature_state",
    "infer_model_kind",
    "ingest_candidate",
    "restore_etalon",
    "validate_candidate",
]

ETALON_SUBMISSION_ID = "seed-test-submission"
"""submission_id эталонного набора (seed_predictions.py, docs/DISTRIBUTION.md)."""

SIGNIFICANT_DELTA = 0.005
"""Порог значимости Δ WAPE-score (clinerule 24 R3: 0.5pp)."""

PredictionRecommendation = Literal[
    "READY_TO_UPLOAD",
    "NEEDS_FIX",
    "WORSE_THAN_PREVIOUS",
    "IDENTICAL_TO_PREVIOUS",
]

_BULK = 500


@dataclass(frozen=True)
class ActiveParams:
    """Параметры активного набора — дефолты для всех read-эндпоинтов."""

    submission_id: str | None
    model_id: str | None
    feature_set: str | None
    zeros_applied: bool | None
    coef_weather: float
    coef_event: float
    coef_season: float
    row_count: int


@dataclass(frozen=True)
class CandidateCheck:
    """Результат валидации CSV+manifest перед ingest."""

    ok: bool
    reason: str
    row_count: int = 0
    holdout_wape_score: float | None = None


@dataclass(frozen=True)
class FeatureState:
    """Состояние тогглов из БД — вход для генерации нового набора (T-230)."""

    feature_set: str
    zeros_applied: bool
    feature_flags: dict[str, bool]
    zero_config: dict[str, Any]
    enabled_features: frozenset[str]


async def feature_state(session: AsyncSession) -> FeatureState:
    """Читает feature_toggles + zero_overrides → параметры генерации.

    Единый источник правды для `feature_set`/`zeros_applied` (раньше логика
    дублировалась в predictions_db.py и load.py).
    """
    toggles = (
        (await session.execute(select(FeatureToggle).order_by(FeatureToggle.name)))
        .scalars()
        .all()
    )
    overrides = (
        (await session.execute(select(ZeroOverride).order_by(ZeroOverride.name)))
        .scalars()
        .all()
    )

    flags = {t.name: bool(t.enabled) for t in toggles}
    enabled = {name for name, on in flags.items() if on}
    if {"use_poi", "use_weather", "use_events"}.issubset(enabled):
        feature_set = "with_all"
    elif "use_poi" in enabled:
        feature_set = "with_poi"
    else:
        feature_set = "baseline"

    zero_config = {o.name: dict(o.params or {}) for o in overrides if o.enabled}
    return FeatureState(
        feature_set=feature_set,
        zeros_applied=bool(zero_config),
        feature_flags=flags,
        zero_config=zero_config,
        enabled_features=frozenset(enabled),
    )


# ─────────────────────────── Чтение ────────────────────────────────────


async def active_params(session: AsyncSession) -> ActiveParams | None:
    """Параметры активного набора (GROUP BY по `is_active`).

    Returns:
        ActiveParams (самый крупный набор, если активных вдруг несколько)
        либо None, если активных строк нет.
    """
    n = func.count(Prediction.id).label("n")
    stmt = (
        select(
            Prediction.submission_id,
            Prediction.model_id,
            Prediction.feature_set,
            Prediction.zeros_applied,
            Prediction.coef_weather,
            Prediction.coef_event,
            Prediction.coef_season,
            n,
        )
        .where(Prediction.is_active.is_(True))
        .group_by(
            Prediction.submission_id,
            Prediction.model_id,
            Prediction.feature_set,
            Prediction.zeros_applied,
            Prediction.coef_weather,
            Prediction.coef_event,
            Prediction.coef_season,
        )
        .order_by(n.desc())
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    return ActiveParams(
        submission_id=row[0],
        model_id=row[1],
        feature_set=row[2],
        zeros_applied=row[3],
        coef_weather=float(row[4]),
        coef_event=float(row[5]),
        coef_season=float(row[6]),
        row_count=int(row[7]),
    )


# ─────────────────────────── Подмена ───────────────────────────────────


async def activate(session: AsyncSession, submission_id: str) -> int:
    """Сделать набор `submission_id` активным (атомарно).

    Raises:
        LookupError: набора с таким submission_id нет в БД.
    """
    available = await session.scalar(
        select(func.count(Prediction.id)).where(
            Prediction.submission_id == submission_id
        )
    )
    if not available:
        raise LookupError(f"prediction set {submission_id!r} not found")

    await session.execute(
        update(Prediction).where(Prediction.is_active.is_(True)).values(is_active=False)
    )
    result = await session.execute(
        update(Prediction)
        .where(Prediction.submission_id == submission_id)
        .values(is_active=True)
    )
    await session.execute(
        update(PredictionRun)
        .where(PredictionRun.submission_id == submission_id)
        .values(activated_at=datetime.now(UTC), status="loaded")
    )
    await session.commit()
    return _rowcount(result)


async def restore_etalon(session: AsyncSession) -> int:
    """Вернуть эталонный набор как активный.

    Raises:
        LookupError: эталонных строк в БД нет (seed не отработал).
    """
    etalon_rows = await session.scalar(
        select(func.count(Prediction.id)).where(Prediction.is_etalon.is_(True))
    )
    if not etalon_rows:
        raise LookupError("etalon rows not found — seed_predictions не отработал")

    await session.execute(
        update(Prediction).where(Prediction.is_active.is_(True)).values(is_active=False)
    )
    result = await session.execute(
        update(Prediction).values(is_active=Prediction.is_etalon)
    )
    await session.execute(
        update(PredictionRun)
        .where(PredictionRun.is_etalon.is_(True))
        .values(activated_at=datetime.now(UTC), status="loaded")
    )
    await session.commit()
    return _rowcount(result)


# ─────────────────────────── Кандидат ──────────────────────────────────


def validate_candidate(csv_path: Path, manifest_path: Path | None) -> CandidateCheck:
    """Проверяет кандидата по clinerule 23 R4 перед ingest.

    Проверки:
      1. CSV внутри `settings.predictions_dir` (защита от path traversal);
      2. manifest рядом и `csv_filename` совпадает с именем CSV;
      3. CSV парсится и не пуст;
      4. `manifest.row_count == len(rows)`;
      5. `manifest.expected_rows == row_count` (drift detect).
    """
    root = Path(settings.predictions_dir).resolve()
    candidate = Path(csv_path).resolve()
    if not candidate.is_relative_to(root):
        return CandidateCheck(False, f"csv outside predictions_dir: {candidate}")
    if not candidate.exists():
        return CandidateCheck(False, f"csv not found: {candidate.name}")

    manifest = read_manifest(manifest_path) if manifest_path else None
    if manifest is None:
        return CandidateCheck(
            False, f"manifest not found for {candidate.with_suffix('.json').name}"
        )
    if manifest.get("csv_filename") != candidate.name:
        return CandidateCheck(
            False,
            f"manifest.csv_filename={manifest.get('csv_filename')!r} != {candidate.name!r}",
        )

    rows = load_predictions_csv(candidate)
    if not rows:
        return CandidateCheck(False, "csv has no parseable rows")
    row_count = len(rows)

    declared = manifest.get("row_count")
    if declared is not None and int(declared) != row_count:
        return CandidateCheck(
            False, f"manifest.row_count={declared} != parsed={row_count}"
        )
    expected = manifest.get("expected_rows")
    if expected is not None and int(expected) != row_count:
        return CandidateCheck(
            False,
            f"NEEDS_FIX: expected_rows={expected} != row_count={row_count}",
            row_count=row_count,
        )

    return CandidateCheck(
        ok=True,
        reason="ok",
        row_count=row_count,
        holdout_wape_score=_as_float(manifest.get("holdout_wape_score")),
    )


async def ingest_candidate(
    session: AsyncSession,
    run: PredictionRun,
    *,
    activate_after: bool = False,
) -> CandidateCheck:
    """INSERT кандидата в `predictions` (is_active=False) + опционально активация.

    Метаданные строк берутся из manifest (source of truth), недостающее —
    из `run.params` (то, что запросил пользователь).

    При ошибке валидации run переводится в `failed`, в БД ничего не пишется.
    """
    csv_path = Path(run.csv_path or "")
    manifest_path = Path(run.manifest_path) if run.manifest_path else None
    check = validate_candidate(csv_path, manifest_path)
    if not check.ok:
        run.status = "failed"
        run.error = check.reason
        await session.commit()
        return check

    manifest: dict[str, Any] = (
        read_manifest(manifest_path) if manifest_path else None
    ) or {}
    params: dict[str, Any] = dict(run.params or {})
    coefs = _resolve_coefs(manifest, params)
    model_id = str(manifest.get("model_id") or params.get("model_id") or "unknown")
    feature_set = str(params.get("feature_set") or "with_all")
    zeros_applied = bool(params.get("zeros_applied", False))

    inserted = await _insert_rows(
        session,
        run=run,
        rows=load_predictions_csv(csv_path),
        model_id=model_id,
        model_version=str(manifest.get("model_version") or "v0.0.1"),
        feature_set=feature_set,
        zeros_applied=zeros_applied,
        feature_flags=dict(params.get("feature_flags") or {}),
        zero_config=dict(params.get("zero_config") or {}),
        coefs=coefs,
        git_commit=manifest.get("git_commit"),
    )

    run.row_count = inserted
    run.holdout_wape_score = check.holdout_wape_score
    run.status = "ready"
    run.error = None
    await session.commit()
    logger.info(
        "ingested run=%s submission=%s rows=%d", run.id, run.submission_id, inserted
    )

    if activate_after and run.submission_id:
        await activate(session, run.submission_id)
    return CandidateCheck(
        ok=True,
        reason=f"ingested {inserted} rows",
        row_count=inserted,
        holdout_wape_score=check.holdout_wape_score,
    )


async def _insert_rows(
    session: AsyncSession,
    *,
    run: PredictionRun,
    rows: list[dict[str, Any]],
    model_id: str,
    model_version: str,
    feature_set: str,
    zeros_applied: bool,
    feature_flags: dict[str, Any],
    zero_config: dict[str, Any],
    coefs: tuple[float, float, float],
    git_commit: str | None,
) -> int:
    """Батчевый INSERT строк набора. Returns число вставленных строк."""
    inserted = 0
    payload: list[Prediction] = []
    for row in rows:
        payload.append(
            Prediction(
                route_id=row["route_id"],
                period_start=row["period_start"],
                period_end=row["period_end"],
                horizon="day",
                granularity="hour",
                value=row["value"],
                lower=None,
                upper=None,
                model_id=model_id,
                model_kind=infer_model_kind(model_id),
                model_version=model_version,
                feature_set=feature_set,
                feature_flags=feature_flags,
                zeros_applied=zeros_applied,
                zero_config=zero_config,
                coef_weather=coefs[0],
                coef_event=coefs[1],
                coef_season=coefs[2],
                submission_id=run.submission_id,
                git_commit=git_commit,
                is_active=False,
                is_etalon=False,
            )
        )
        if len(payload) >= _BULK:
            session.add_all(payload)
            await session.commit()
            inserted += len(payload)
            payload = []
    if payload:
        session.add_all(payload)
        await session.commit()
        inserted += len(payload)
    return inserted


# ─────────────────────────── Helpers ───────────────────────────────────


def build_recommendation(
    candidate: float | None, active: float | None
) -> PredictionRecommendation:
    """Вердикт по clinerule 24 R3 (WAPE-score: больше = лучше, clinerule 27)."""
    if candidate is None or active is None:
        return "READY_TO_UPLOAD"
    delta = candidate - active
    if abs(delta) <= SIGNIFICANT_DELTA:
        return "IDENTICAL_TO_PREVIOUS"
    return "READY_TO_UPLOAD" if delta > 0 else "WORSE_THAN_PREVIOUS"


def infer_model_kind(model_id: str) -> str:
    """model_id → model_kind (baseline|xgboost|catboost|gru|hybrid)."""
    lowered = model_id.lower()
    for kind in ("xgboost", "catboost", "gru", "hybrid"):
        if kind in lowered:
            return kind
    return "baseline"


def _resolve_coefs(
    manifest: dict[str, Any], params: dict[str, Any]
) -> tuple[float, float, float]:
    """Коэффициенты: manifest (source of truth) → params → 1.0."""
    coefficients = manifest.get("coefficients") or {}
    return (
        _first_float(
            coefficients.get("weather"),
            coefficients.get("coef_weather"),
            params.get("coef_weather"),
        ),
        _first_float(
            coefficients.get("event"),
            coefficients.get("coef_event"),
            params.get("coef_event"),
        ),
        _first_float(
            coefficients.get("season"),
            coefficients.get("coef_season"),
            params.get("coef_season"),
        ),
    )


def _first_float(*candidates: object) -> float:
    """Первый не-None, приводимый к float; иначе 1.0."""
    for cand in candidates:
        value = _as_float(cand)
        if value is not None:
            return value
    return 1.0


def _as_float(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _rowcount(result: object) -> int:
    """Число затронутых строк из результата UPDATE (asyncpg/aiosqlite)."""
    return int(getattr(result, "rowcount", 0) or 0)
