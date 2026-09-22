#!/usr/bin/env python3
"""CLI для evaluate pipeline (T-035).

Usage:
    # Активная модель (из ml/artifacts/active.json)
    make evaluate

    # Явный model_id
    uv run --directory ml python scripts/evaluate.py --model-id xgboost_v1

    # Свой holdout
    uv run --directory ml python scripts/evaluate.py --holdout-days 14

Output:
    - stdout: одна строка с метриками
    - ml/artifacts/<model_id>/meta.json: metrics обновлён
    - docs/reports/evaluate_<model>_<date>.md: подробный markdown отчёт
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.training.evaluate import evaluate_artifact
from transit_ai.training.registry import ModelRegistry

ROOT = Path(__file__).resolve().parents[1]  # ml/
REPO_ROOT = ROOT.parent


def _resolve_model_id(args_model_id: str | None) -> str:
    """Resolve model_id: --model-id > active.json > error."""
    if args_model_id:
        return args_model_id
    reg = ModelRegistry()
    active = reg.get_active_id()
    if not active:
        print(
            "❌ No --model-id given and active.json missing or empty.\n"
            "Hint: run `make train-baseline` first, or pass --model-id.",
            file=sys.stderr,
        )
        sys.exit(2)
    return active


def _load_holdout_data(n_days: int) -> pd.DataFrame:
    """Load synthetic ridership for smoke testing.

    T-035 пока работает на synthetic (real data подключится в T-026).
    SyntheticSource использует фиксированный epoch (см. data/synthetic.py),
    диапазон [epoch, epoch + n_days дней]. Передаём валидный DateRange.
    """
    from datetime import datetime, timedelta

    from transit_ai.data.base import DateRange

    src = SyntheticSource(SyntheticConfig(n_days=n_days, seed=42))
    epoch = datetime(2026, 1, 1)  # noqa: DTZ001 — SyntheticSource сравнивает tz-naive внутри
    return src.load_ridership(DateRange(epoch, epoch + timedelta(days=n_days - 1)))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--model-id",
        default=None,
        help="Model ID из ml/artifacts/. Default: active.json.",
    )
    p.add_argument(
        "--holdout-days",
        type=int,
        default=7,
        help="Сколько последних дней использовать как holdout (default: 7).",
    )
    p.add_argument(
        "--n-days",
        type=int,
        default=35,
        help="Сколько дней синтетики сгенерить (default: 35 = 28 train + 7 holdout).",
    )
    p.add_argument(
        "--reports-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "reports",
        help="Куда писать markdown report (default: docs/reports/).",
    )
    args = p.parse_args()

    model_id = _resolve_model_id(args.model_id)
    print(f"📊 Evaluating {model_id!r} (holdout_days={args.holdout_days})")

    ridership_df = _load_holdout_data(args.n_days)
    reg = ModelRegistry()  # default = ml/artifacts/

    try:
        result = evaluate_artifact(
            model_id=model_id,
            ridership_df=ridership_df,
            registry=reg,
            holdout_days=args.holdout_days,
            reports_dir=args.reports_dir,
        )
    except (FileNotFoundError, NotImplementedError, ValueError) as e:
        print(f"❌ Evaluation failed: {e}", file=sys.stderr)
        return 1

    print()
    print(f"  RMSLE  = {result.metrics['rmsle']:.4f}")
    print(f"  MAE    = {result.metrics['mae']:.2f}")
    print(f"  MAPE % = {result.metrics['mape']:.2f}")
    print()
    print(f"  n_points = {result.n_points}")
    print(f"  eval_seconds = {result.eval_seconds:.2f}")
    print(f"  report = {result.report_path}")
    print("  meta.json обновлён (metrics заполнены)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
