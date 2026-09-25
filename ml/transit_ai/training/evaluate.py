"""Production evaluation pipeline (T-035).

Pipeline:
  1. Load fitted Predictor via registry.load(model_id) [dispatch by meta['kind']]
  2. Split ridership_df → последние holdout_days = holdout
  3. Для каждой строки holdout: predictor.predict(stop_id, ts, ts+1h)[0].value
     vs actual passenger_count → y_pred/y_true
  4. compute_metrics(y_true, y_pred) → {rmsle, mae, mape}
  5. registry.update_metrics(model_id, metrics) → meta.json.metrics
  6. Write markdown report в docs/reports/evaluate_<model>_<date>.md

In-memory подход (не parquet): T-035 независим от T-033 (predict.py).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from transit_ai.reports.metrics import compute_metrics
from transit_ai.training.registry import ModelRegistry

logger = logging.getLogger("evaluate")

# Hard limits из clinerule 19-ml-benchmark-pipeline.md (CI gates)
THRESHOLDS: dict[str, float] = {
    "rmsle": 0.5,
    "mae": 15.0,
    "mape": 25.0,
}

# Reports dir (auto-created). Override via TRANSIT_AI_REPORTS_DIR env.
DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[3] / "docs" / "reports"


@dataclass(frozen=True)
class EvaluationResult:
    """Результат evaluate_artifact: метрики + метаданные + путь к отчёту."""

    model_id: str
    metrics: dict[str, float]
    n_points: int
    eval_seconds: float
    holdout_start: datetime
    holdout_end: datetime
    report_path: Path | None
    git_commit: str = "unknown"


def _split_holdout(
    ridership_df: pd.DataFrame,
    holdout_days: int,
) -> tuple[pd.DataFrame, pd.DataFrame, datetime, datetime]:
    """Split ridership по последним holdout_days дней.

    Returns: (train_context, holdout, holdout_start, holdout_end).

    Note: 'train_context' — это ВСЯ ridership_df до holdout, нужна только для
    инференса (predictor.predict использует fitted state, не свежие данные).
    Возвращается для совместимости с будущим T-037 (plots).
    """
    if holdout_days < 1:
        raise ValueError(f"holdout_days must be >= 1 (got {holdout_days})")

    df = ridership_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    max_date = df["timestamp"].max()
    cutoff = max_date - pd.Timedelta(days=holdout_days)

    holdout = df[df["timestamp"] > cutoff].reset_index(drop=True)
    train_context = df[df["timestamp"] <= cutoff].reset_index(drop=True)

    if holdout.empty:
        raise ValueError(
            f"Holdout is empty after splitting by {holdout_days} days. "
            f"ridership_df has {len(df)} rows from {df['timestamp'].min()} "
            f"to {max_date}."
        )

    holdout_start = holdout["timestamp"].min().to_pydatetime()
    holdout_end = holdout["timestamp"].max().to_pydatetime()
    return train_context, holdout, holdout_start, holdout_end


def _format_thresholds_table(metrics: dict[str, float]) -> str:
    """Markdown table with threshold + status per metric."""
    rows = [
        "| Metric | Value | Threshold | Status |",
        "|--------|-------|-----------|--------|",
    ]
    for name in ("rmsle", "mae", "mape"):
        value = metrics.get(name, 0.0)
        threshold = THRESHOLDS.get(name, float("inf"))
        status = "✅" if value <= threshold else "❌"
        rows.append(f"| {name.upper()} | {value:.4f} | ≤ {threshold} | {status} |")
    return "\n".join(rows)


def _write_report(
    result: EvaluationResult,
    reports_dir: Path,
) -> Path:
    """Write markdown report. Возвращает путь к файлу."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_str = result.holdout_end.date().isoformat()
    report_path = reports_dir / f"evaluate_{result.model_id}_{date_str}.md"

    content = f"""# Evaluation Report — {result.model_id}

Generated: {datetime.now(UTC).isoformat()}
Git commit: {result.git_commit}
Holdout: {result.holdout_start.isoformat()} .. {result.holdout_end.isoformat()}
N points evaluated: {result.n_points}
Eval time: {result.eval_seconds:.2f}s

## Metrics

{_format_thresholds_table(result.metrics)}

## Notes

- In-memory evaluation (predictor.predict on holdout, not parquet-based)
- Metrics from `transit_ai.reports.metrics` (single source of truth)
- Thresholds from clinerule 19 (CI gate values)
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path


def evaluate_artifact(
    model_id: str,
    ridership_df: pd.DataFrame,
    registry: ModelRegistry,
    holdout_days: int = 7,
    reports_dir: Path | None = None,
) -> EvaluationResult:
    """Полный eval pipeline: load → predict → metrics → update meta → write report.

    Args:
        model_id: ID артефакта в registry.artifacts_dir (напр. "baseline_v1").
        ridership_df: DataFrame с колонками [timestamp, stop_id, route_id, passenger_count].
        registry: ModelRegistry, через который грузим predictor и обновляем meta.json.
        holdout_days: Сколько последних дней ridership_df использовать как holdout.
        reports_dir: Куда писать markdown report (default: docs/reports/).

    Returns:
        EvaluationResult с метриками и метаданными (включая report_path).

    Raises:
        FileNotFoundError: artifact или meta.json отсутствуют.
        NotImplementedError: kind артефакта не поддерживается dispatcher'ом.
        ValueError: holdout пустой или holdout_days < 1.
    """
    start = time.time()

    # 1. Load fitted predictor через registry (dispatch by kind)
    predictor = registry.load(model_id)
    logger.info(f"Loaded predictor {model_id!r} (kind={predictor.kind!r})")

    # 2. Split ridership на train/holdout
    _, holdout, holdout_start, holdout_end = _split_holdout(ridership_df, holdout_days)
    logger.info(
        f"Holdout: {holdout_start.isoformat()} .. {holdout_end.isoformat()} "
        f"({len(holdout)} rows)"
    )

    # 3. Predict для каждой строки holdout
    y_true: list[float] = []
    y_pred: list[float] = []
    for row in holdout.itertuples(index=False):
        ts = pd.Timestamp(row.timestamp).to_pydatetime()
        stop_id = int(row.stop_id)
        actual = float(row.passenger_count)
        try:
            pts = predictor.predict(stop_id, ts, ts + timedelta(hours=1))
            pred = float(pts[0].value) if pts else 0.0
        except Exception as e:  # noqa: BLE001 — predictor может бросить на редких кейсах
            logger.warning(f"predict() failed for stop={stop_id} ts={ts}: {e}")
            continue
        y_true.append(max(actual, 0.0))
        y_pred.append(max(pred, 0.0))

    if not y_true:
        raise RuntimeError(
            f"No predictions produced for {len(holdout)} holdout rows. "
            f"Check predictor and data."
        )

    # 4. Compute metrics (single source of truth: reports.metrics)
    metrics = compute_metrics(np.asarray(y_true), np.asarray(y_pred))

    # 5. Update meta.json.metrics (preserves git_commit/seed/trained_at)
    registry.update_metrics(model_id, metrics)

    # 6. Write report
    out_dir = reports_dir if reports_dir is not None else DEFAULT_REPORTS_DIR
    elapsed = time.time() - start

    # Достаём git_commit из свежепрочитанной meta.json (для отчёта)
    meta = json.loads((registry.artifacts_dir / model_id / "meta.json").read_text())

    report_path = _write_report(
        EvaluationResult(
            model_id=model_id,
            metrics=metrics,
            n_points=len(y_true),
            eval_seconds=elapsed,
            holdout_start=holdout_start,
            holdout_end=holdout_end,
            report_path=None,
            git_commit=meta.get("git_commit", "unknown"),
        ),
        out_dir,
    )

    result = EvaluationResult(
        model_id=model_id,
        metrics=metrics,
        n_points=len(y_true),
        eval_seconds=elapsed,
        holdout_start=holdout_start,
        holdout_end=holdout_end,
        report_path=report_path,
        git_commit=meta.get("git_commit", "unknown"),
    )

    logger.info(
        f"✅ Evaluated {model_id}: rmsle={metrics['rmsle']:.4f} "
        f"mae={metrics['mae']:.2f} mape={metrics['mape']:.2f}% "
        f"in {elapsed:.1f}s"
    )
    return result


__all__ = ["DEFAULT_REPORTS_DIR", "THRESHOLDS", "EvaluationResult", "evaluate_artifact"]
