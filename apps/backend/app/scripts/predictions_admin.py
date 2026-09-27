"""CLI управления наборами прогнозов (T-230).

Когда UI не поллит Celery (или нужно из терминала):

    uv run --package transit-ai-backend python -m app.scripts.predictions_admin list
    ... activate --submission-id ui-20260927T161500Z
    ... restore-etalon
    ... ingest --run-id 12 [--no-activate]
    ... ingest-path --csv predictions/submission_x.csv [--activate]

Инвариант: строки не удаляются — только флаги `is_active` / `is_etalon`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db import _get_sessionmaker
from app.models import PredictionRun
from app.predictions_active import (
    activate,
    active_params,
    feature_state,
    ingest_candidate,
    restore_etalon,
)
from app.predictions_csv import read_manifest


def _cmd_list() -> int:
    async def run() -> None:
        Session = _get_sessionmaker()
        async with Session() as session:
            rows = (
                (
                    await session.execute(
                        select(PredictionRun)
                        .order_by(PredictionRun.id.desc())
                        .limit(20)
                    )
                )
                .scalars()
                .all()
            )
            active = await active_params(session)
            print(f"active_submission_id = {active.submission_id if active else None}")
            print(f"active_rows          = {active.row_count if active else 0}")
            for r in rows:
                print(
                    f"  #{r.id} {r.status:<9} {r.submission_id or '-':<24} "
                    f"rows={r.row_count or 0:<6} holdout={r.holdout_wape_score} "
                    f"rec={r.recommendation or '-'}"
                )

    asyncio.run(run())
    return 0


def _cmd_activate(submission_id: str) -> int:
    async def run() -> int:
        Session = _get_sessionmaker()
        async with Session() as session:
            try:
                rows = await activate(session, submission_id)
            except LookupError as exc:
                print(f"ERROR: {exc}")
                return 1
            print(f"✓ activated {submission_id} ({rows} rows)")
            return 0

    return asyncio.run(run())


def _cmd_restore_etalon() -> int:
    async def run() -> int:
        Session = _get_sessionmaker()
        async with Session() as session:
            try:
                rows = await restore_etalon(session)
            except LookupError as exc:
                print(f"ERROR: {exc}")
                return 1
            print(f"✓ etalon restored ({rows} rows active)")
            return 0

    return asyncio.run(run())


def _cmd_ingest(run_id: int, activate_after: bool) -> int:
    async def run() -> int:
        Session = _get_sessionmaker()
        async with Session() as session:
            run = await session.get(PredictionRun, run_id)
            if run is None:
                print(f"ERROR: run {run_id} not found")
                return 1
            check = await ingest_candidate(session, run, activate_after=activate_after)
            print(f"{'✓' if check.ok else '✗'} {check.reason}")
            return 0 if check.ok else 1

    return asyncio.run(run())


def _cmd_ingest_path(csv_path: Path, activate_after: bool) -> int:
    manifest_path = csv_path.with_suffix(".json")

    async def run() -> int:
        manifest = read_manifest(manifest_path)
        if manifest is None:
            print(f"ERROR: manifest not found: {manifest_path}")
            return 1
        Session = _get_sessionmaker()
        async with Session() as session:
            state = await feature_state(session)
            run = PredictionRun(
                celery_task_id=f"cli-{manifest.get('submission_id', csv_path.stem)}",
                task_name="cli.ingest",
                status="ready",
                submission_id=str(manifest.get("submission_id") or csv_path.stem),
                model_id=str(manifest.get("model_id") or "unknown"),
                feature_set=state.feature_set,
                pipeline_kind="cli",
                csv_path=str(csv_path),
                manifest_path=str(manifest_path),
                params={
                    "feature_set": state.feature_set,
                    "zeros_applied": state.zeros_applied,
                    "feature_flags": dict(state.feature_flags),
                    "zero_config": dict(state.zero_config),
                },
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            check = await ingest_candidate(session, run, activate_after=activate_after)
            print(
                json.dumps(
                    {
                        "run_id": run.id,
                        "submission_id": run.submission_id,
                        "rows": check.row_count,
                        "holdout": check.holdout_wape_score,
                        "ok": check.ok,
                        "reason": check.reason,
                    },
                    ensure_ascii=False,
                )
            )
            return 0 if check.ok else 1

    return asyncio.run(run())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Управление наборами прогнозов (T-230)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Список запусков + активный набор")

    p_act = sub.add_parser("activate", help="Сделать набор активным")
    p_act.add_argument("--submission-id", required=True)

    sub.add_parser("restore-etalon", help="Вернуть эталонный набор")

    p_ing = sub.add_parser("ingest", help="Загрузить кандидата по run_id")
    p_ing.add_argument("--run-id", type=int, required=True)
    p_ing.add_argument("--no-activate", action="store_true")

    p_path = sub.add_parser("ingest-path", help="Загрузить CSV+manifest с диска")
    p_path.add_argument("--csv", type=Path, required=True)
    p_path.add_argument("--no-activate", action="store_true")

    args = parser.parse_args()
    if args.cmd == "list":
        return _cmd_list()
    if args.cmd == "activate":
        return _cmd_activate(args.submission_id)
    if args.cmd == "restore-etalon":
        return _cmd_restore_etalon()
    if args.cmd == "ingest":
        return _cmd_ingest(args.run_id, not args.no_activate)
    return _cmd_ingest_path(args.csv, not args.no_activate)


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["main"]
