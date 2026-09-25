"""SUBMISSION CANDIDATE block generator (T-149, clinerule 24).

После каждого ML-скрипта, который генерит submission кандидат, должен выводиться
блок SUBMISSION CANDIDATE с явной рекомендацией (READY_TO_UPLOAD / NEEDS_FIX /
WORSE_THAN_PREVIOUS / IDENTICAL_TO_PREVIOUS) и сравнением с предыдущим submission.

Использование:
    from transit_ai.submission.candidate import print_candidate

    print_candidate(
        csv_path=Path("predictions/submission_x_..._.csv"),
        manifest_path=Path("predictions/submission_x_..._.json"),
        model_id="xgboost_v2",
        submission_id="v5-xgboost",
        holdout_wape=0.8123,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=13_500_000.0,
    )
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = ["CandidateInfo", "Recommendation", "print_candidate"]


class Recommendation(str, Enum):
    """Recommendation enum для SUBMISSION CANDIDATE block (R3 clinerule 24)."""

    READY_TO_UPLOAD = "READY_TO_UPLOAD"
    NEEDS_FIX = "NEEDS_FIX"
    WORSE_THAN_PREVIOUS = "WORSE_THAN_PREVIOUS"
    IDENTICAL_TO_PREVIOUS = "IDENTICAL_TO_PREVIOUS"


# Threshold: delta < DELTA_THRESHOLD считается шумом (не лучше, не хуже)
DELTA_THRESHOLD = 0.005  # 0.5pp


@dataclass(frozen=True)
class CandidateInfo:
    """Structured info для SUBMISSION CANDIDATE блока."""

    csv_path: Path
    manifest_path: Path
    model_id: str
    submission_id: str
    holdout_wape: float
    submission_start: str
    submission_end: str
    row_count: int
    total_predictions: float
    expected_rows: int | None = None
    previous_platform_wape: float | None = None
    previous_submission_id: str | None = None
    previous_evidence_id: str | None = None

    def compute_recommendation(self) -> Recommendation:
        """Вычислить recommendation (R3 clinerule 24)."""
        # R3.NEEDS_FIX: row_count != expected_rows
        if self.expected_rows is not None and self.row_count != self.expected_rows:
            return Recommendation.NEEDS_FIX
        # R3.READY_TO_UPLOAD: первый submission (нет previous)
        if self.previous_platform_wape is None:
            return Recommendation.READY_TO_UPLOAD
        delta = self.holdout_wape - self.previous_platform_wape
        # R3.IDENTICAL_TO_PREVIOUS: delta < threshold
        if abs(delta) < DELTA_THRESHOLD:
            return Recommendation.IDENTICAL_TO_PREVIOUS
        # R3.READY_TO_UPLOAD: holdout лучше (WAPE выросла)
        if delta > 0:
            return Recommendation.READY_TO_UPLOAD
        # R3.WORSE_THAN_PREVIOUS: holdout хуже
        return Recommendation.WORSE_THAN_PREVIOUS


def _find_previous_submission(
    predictions_dir: Path,
) -> tuple[float, str, str] | None:
    """Найти самый новый manifest с platform_submitted=true (R4 clinerule 24).

    Returns:
        (platform_score, submission_id, evidence_id) или None.
        evidence_id = submission_id предыдущего (для ссылки на F-NNN в ledger).
    """
    if not predictions_dir.exists():
        return None
    candidates: list[tuple[float, Path, dict]] = []
    for f in predictions_dir.glob("*.json"):
        try:
            d = json.loads(f.read_text())
            if d.get("platform_submitted") and d.get("platform_score") is not None:
                candidates.append((f.stat().st_mtime, f, d))
        except (json.JSONDecodeError, OSError):
            continue
    if not candidates:
        return None
    candidates.sort(reverse=True)  # newest first
    _, _, d = candidates[0]
    return (
        float(d["platform_score"]),
        str(d.get("submission_id", "unknown")),
        str(d.get("submission_id", "unknown")),
    )


def print_candidate(
    csv_path: Path,
    manifest_path: Path,
    model_id: str,
    submission_id: str,
    holdout_wape: float,
    submission_start: str,
    submission_end: str,
    row_count: int,
    total_predictions: float,
    expected_rows: int | None = None,
    predictions_dir: Path | None = None,
) -> str:
    """Вывести SUBMISSION CANDIDATE блок в stdout и вернуть его как строку.

    Используется после каждого ML запуска (clinerule 24).
    Блок парсится регуляркой (R2): фиксированные заголовки строк.
    """
    if predictions_dir is None:
        predictions_dir = csv_path.parent

    try:
        prev = _find_previous_submission(predictions_dir)
        prev_score = prev[0] if prev else None
        prev_sub_id = prev[1] if prev else None
        prev_ev_id = prev[2] if prev else None
    except (OSError, json.JSONDecodeError, KeyError, IndexError):  # R5
        prev_score = prev_sub_id = prev_ev_id = None

    info = CandidateInfo(
        csv_path=csv_path.resolve(),
        manifest_path=manifest_path.resolve(),
        model_id=model_id,
        submission_id=submission_id,
        holdout_wape=holdout_wape,
        submission_start=submission_start,
        submission_end=submission_end,
        row_count=row_count,
        total_predictions=total_predictions,
        expected_rows=expected_rows,
        previous_platform_wape=prev_score,
        previous_submission_id=prev_sub_id,
        previous_evidence_id=prev_ev_id,
    )
    rec = info.compute_recommendation()

    prev_line = (
        f"{info.previous_platform_wape:.5f} ({info.previous_evidence_id})"
        if info.previous_platform_wape is not None
        else "none"
    )

    lines = [
        "=" * 60,
        "SUBMISSION CANDIDATE",
        "=" * 60,
        f"CSV:           {info.csv_path}",
        f"Manifest:      {info.manifest_path}",
        f"Model:         {info.model_id}",
        f"Submission ID: {info.submission_id}",
        f"Holdout WAPE:  {info.holdout_wape:.4f}",
        f"Date range:    {info.submission_start} → {info.submission_end}",
        f"Rows:          {info.row_count:,}",
        f"Total preds:   {info.total_predictions:,.0f}",
        f"Recommendation: {rec.value}",
        f"Platform prev: {prev_line}",
        "=" * 60,
    ]
    block = "\n".join(lines)
    print(block)
    return block
