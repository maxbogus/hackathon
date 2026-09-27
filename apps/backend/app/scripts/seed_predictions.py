"""Seed predictions and actuals from data/real/*.csv into PostgreSQL.

Designed to be called from apps/backend/scripts/entrypoint.sh OR directly via:
    cd apps/backend && uv run python -m app.scripts.seed_predictions

Что делает:
  1. Проверяет, что таблицы actuals/predictions пустые (idempotent — skip если уже есть данные).
  2. actuals: читает data/real/train.csv (8 GB) chunked → агрегирует boardings по (route_id, hour)
     → INSERT в actuals (68801 строк ожидается).
  3. predictions: читает data/real/test_submission.csv (эталон с route 5 = 0) →
     INSERT в predictions (14640 строк ожидается).

CLI:
  --dry-run           print counts, no DB writes
  --data-dir PATH     override data dir (default: REPO_ROOT/data)
  --batch-size N      actials chunk size (default 50000)
  --actuals-only      только actuals (skip predictions)
  --predictions-only  только predictions (skip actuals)

Все настройки берутся из app.config.settings (TRANSIT_AI_DATABASE_URL).

КРИТИЧНО:
  - train.csv имеет колонку `ngpt_route` ("25 трамвай" → 25). Парсим в int.
  - test_submission.csv использует separator=";" (НЕ ",").
  - route 5 = 0 в эталоне (cold start F-051). Этот эталон даёт WAPE-score=0.8751.
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import _get_sessionmaker
from app.models import Actual, FeatureToggle, Prediction, ZeroOverride
from app.scripts._parsers import parse_float as _parse_float
from app.scripts._parsers import parse_int as _parse_int
from app.scripts._parsers import parse_route_id as _parse_route_id

logger = logging.getLogger("seed_predictions")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "data"


def aggregate_actuals_csv(
    csv_path: Path, batch_size: int = 50_000
) -> dict[tuple[int, datetime], int]:
    """Читает train.csv chunked → возвращает {(route_id, hour_start): boardings_count}.

    Подсчёт — кол-во валидных транзакций (validation_result=1, pass_route="НГПТ").
    Час агрегируется по tran_date_time (НЕ begin_date_time, т.к. это валидация пассажира).
    """
    counts: dict[tuple[int, datetime], int] = defaultdict(int)
    total_rows = 0
    valid_rows = 0
    skipped_route = 0

    if not csv_path.exists():
        logger.warning("actuals CSV not found: %s", csv_path)
        return {}

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            total_rows += 1
            # Только успешные валидации (1) и обычные НГПТ поездки
            if row.get("validation_result") != "1":
                continue
            if row.get("pass_route") != "НГПТ":
                continue

            route_id = _parse_route_id(row.get("ngpt_route", ""))
            if route_id is None:
                skipped_route += 1
                continue

            ts_raw = row.get("tran_date_time") or ""
            try:
                ts = datetime.fromisoformat(ts_raw).replace(
                    minute=0, second=0, microsecond=0
                )
            except ValueError:
                continue

            counts[(route_id, ts)] += 1
            valid_rows += 1

            if total_rows % batch_size == 0:
                logger.info(
                    "  ...processed %d rows, valid=%d, unique_keys=%d",
                    total_rows,
                    valid_rows,
                    len(counts),
                )

    logger.info(
        "Aggregated %d/%d rows (%d skipped_route), %d unique (route,hour) keys",
        valid_rows,
        total_rows,
        skipped_route,
        len(counts),
    )
    return counts


def load_predictions_csv(csv_path: Path) -> list[dict]:
    """Читает test_submission.csv → список dict с ключами для INSERT.

    Ожидаемый формат: route;date;hour;prediction (separator=";").
    Returns list of dict с полями: route_id, period_start, period_end, value.
    """
    rows: list[dict] = []
    if not csv_path.exists():
        logger.warning("predictions CSV not found: %s", csv_path)
        return rows

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            route_id = _parse_int(row.get("route"))
            hour = _parse_int(row.get("hour"))
            date_raw = (row.get("date") or "").strip()
            value = _parse_float(row.get("prediction"))
            if route_id is None or hour is None or not date_raw or value is None:
                continue
            try:
                date = datetime.fromisoformat(date_raw)
            except ValueError:
                continue
            period_start = date.replace(hour=hour, minute=0, second=0, microsecond=0)
            if period_start.tzinfo is None:
                period_start = period_start.replace(tzinfo=UTC)
            period_end = period_start + timedelta(hours=1)
            rows.append(
                {
                    "route_id": route_id,
                    "period_start": period_start,
                    "period_end": period_end,
                    "value": float(value),
                }
            )
    logger.info("Loaded %d prediction rows from %s", len(rows), csv_path.name)
    return rows


async def _count_actuals(session: AsyncSession) -> int:
    from sqlalchemy import func

    res = await session.execute(select(func.count(Actual.id)))
    return int(res.scalar() or 0)


async def _count_predictions(session: AsyncSession) -> int:
    from sqlalchemy import func

    res = await session.execute(select(func.count(Prediction.id)))
    return int(res.scalar() or 0)


async def _seed_actuals(
    session: AsyncSession, data_dir: Path, batch_size: int, dry_run: bool
) -> int:
    """INSERT actuals. Returns inserted count."""
    existing = await _count_actuals(session)
    if existing > 0:
        logger.info("actuals already has %d rows → skip", existing)
        return 0

    train_csv = data_dir / "real" / "train.csv"
    test_csv = data_dir / "real" / "test.csv"
    csv_path = train_csv if train_csv.exists() else test_csv
    if not csv_path.exists():
        logger.error("Neither train.csv nor test.csv found in %s/real", data_dir)
        return 0

    aggregated = aggregate_actuals_csv(csv_path, batch_size=batch_size)
    if not aggregated:
        return 0

    if dry_run:
        logger.info("[DRY-RUN] would INSERT %d actuals rows", len(aggregated))
        return len(aggregated)

    inserted = 0
    BULK = 500
    payload: list[Actual] = []
    for (route_id, hour_start), count in aggregated.items():
        payload.append(
            Actual(
                route_id=int(route_id),
                period_start=hour_start.replace(tzinfo=UTC)
                if hour_start.tzinfo is None
                else hour_start,
                period_end=(hour_start + timedelta(hours=1)).replace(tzinfo=UTC),
                value=float(count),
            )
        )
        if len(payload) >= BULK:
            session.add_all(payload)
            await session.commit()
            inserted += len(payload)
            payload = []
            logger.info("  ...inserted %d actuals", inserted)

    if payload:
        session.add_all(payload)
        await session.commit()
        inserted += len(payload)

    logger.info("✓ Inserted %d actuals rows", inserted)
    return inserted


async def _seed_predictions(
    session: AsyncSession, data_dir: Path, dry_run: bool
) -> int:
    """INSERT predictions from test_submission.csv. Returns inserted count."""
    existing = await _count_predictions(session)
    if existing > 0:
        logger.info("predictions already has %d rows → skip", existing)
        return 0

    sub_csv = data_dir / "real" / "test_submission.csv"
    rows = load_predictions_csv(sub_csv)
    if not rows:
        return 0

    if dry_run:
        logger.info("[DRY-RUN] would INSERT %d predictions rows", len(rows))
        return len(rows)

    inserted = 0
    BULK = 500
    payload: list[Prediction] = []
    for r in rows:
        payload.append(
            Prediction(
                route_id=r["route_id"],
                period_start=r["period_start"],
                period_end=r["period_end"],
                horizon="day",
                granularity="hour",
                value=r["value"],
                lower=None,
                upper=None,
                model_id="test_submission_baseline",
                model_kind="baseline",
                model_version="v0.0.1",
                feature_set="with_all",
                feature_flags={
                    "use_poi": True,
                    "use_weather": True,
                    "use_events": True,
                    "use_seasonal": True,
                    "use_lag": True,
                    "use_traffic": False,
                },
                zeros_applied=True,
                zero_config={
                    "zero_route_5": True,
                    "zero_night_pred_cap": 55,
                },
                coef_weather=1.0,
                coef_event=1.0,
                coef_season=1.0,
                submission_id="seed-test-submission",
                git_commit=None,
            )
        )
        if len(payload) >= BULK:
            session.add_all(payload)
            await session.commit()
            inserted += len(payload)
            payload = []
            logger.info("  ...inserted %d predictions", inserted)

    if payload:
        session.add_all(payload)
        await session.commit()
        inserted += len(payload)

    logger.info("✓ Inserted %d predictions rows", inserted)
    return inserted


async def _verify_features(session: AsyncSession) -> None:
    """Логирует текущее состояние feature_toggles / zero_overrides.

    Эти таблицы заполняются alembic миграцией (T-194). Если пусты — warning.
    """
    from sqlalchemy import func

    ft_count = (
        await session.execute(select(func.count(FeatureToggle.id)))
    ).scalar() or 0
    zo_count = (
        await session.execute(select(func.count(ZeroOverride.id)))
    ).scalar() or 0
    logger.info(
        "feature_toggles=%d, zero_overrides=%d (seeded by alembic migration)",
        ft_count,
        zo_count,
    )
    if ft_count == 0 or zo_count == 0:
        logger.warning(
            "feature_toggles/zero_overrides пусты — alembic seed не отработал?"
        )


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Seed DB with predictions + actuals.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--batch-size", type=int, default=50_000)
    parser.add_argument("--actuals-only", action="store_true")
    parser.add_argument("--predictions-only", action="store_true")
    args = parser.parse_args()

    if not args.data_dir.exists():
        logger.error("Data dir not found: %s", args.data_dir)
        return 1

    logger.info("Connecting to DB: %s", settings.database_url.split("@")[-1])
    Session = _get_sessionmaker()
    async with Session() as session:
        await _verify_features(session)
        if not args.predictions_only:
            await _seed_actuals(session, args.data_dir, args.batch_size, args.dry_run)
        if not args.actuals_only:
            await _seed_predictions(session, args.data_dir, args.dry_run)
    logger.info("Seed done.")
    return 0


def main() -> int:
    import asyncio

    return asyncio.run(amain())


if __name__ == "__main__":
    raise SystemExit(main())
