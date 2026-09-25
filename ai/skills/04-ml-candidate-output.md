# Skill: ml-candidate-output — SUBMISSION CANDIDATE block после ML запусков

**Когда подключать:** при работе над T-149, T-152 или любым ML-скриптом
который генерит submission кандидат.

## Зачем этот скилл

Clinerule 24 требует чтобы после каждого ML скрипта выводился блок
`SUBMISSION CANDIDATE` с recommendation (READY_TO_UPLOAD / NEEDS_FIX /
WORSE_THAN_PREVIOUS / IDENTICAL_TO_PREVIOUS). Без этого пользователь должен
сам сравнивать кандидатов и решать что заливать (источник ошибок F-021).

## Реализация helper'а

### `ml/transit_ai/submission/candidate.py`

```python
"""SUBMISSION CANDIDATE block generator (T-149, clinerule 24).

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
        previous_platform_wape=0.73231,  # из manifest предыдущего
        previous_submission_id="v3-bias-calibration",
        previous_evidence_id="F-023",
    )
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = ["Recommendation", "CandidateInfo", "print_candidate"]


class Recommendation(str, Enum):
    READY_TO_UPLOAD = "READY_TO_UPLOAD"
    NEEDS_FIX = "NEEDS_FIX"
    WORSE_THAN_PREVIOUS = "WORSE_THAN_PREVIOUS"
    IDENTICAL_TO_PREVIOUS = "IDENTICAL_TO_PREVIOUS"


# Threshold: delta < THRESHOLD считается шумом (не лучше, не хуже)
DELTA_THRESHOLD = 0.005  # 0.5pp


@dataclass(frozen=True)
class CandidateInfo:
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
        # NEEDS_FIX если row_count mismatch
        if self.expected_rows is not None and self.row_count != self.expected_rows:
            return Recommendation.NEEDS_FIX
        # Первый submission — всегда READY
        if self.previous_platform_wape is None:
            return Recommendation.READY_TO_UPLOAD
        delta = self.holdout_wape - self.previous_platform_wape
        if abs(delta) < DELTA_THRESHOLD:
            return Recommendation.IDENTICAL_TO_PREVIOUS
        if delta > 0:
            return Recommendation.READY_TO_UPLOAD  # WAPE: выше = лучше
        return Recommendation.WORSE_THAN_PREVIOUS


def _find_previous_submission(predictions_dir: Path) -> tuple[float, str, str] | None:
    """Найти самый новый manifest с platform_submitted=true."""
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
        d.get("submission_id", "unknown"),
        d.get("submission_id", "unknown"),  # evidence id = submission_id если нет ledger link
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
    """
    if predictions_dir is None:
        predictions_dir = csv_path.parent

    prev = _find_previous_submission(predictions_dir)
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
        previous_platform_wape=prev[0] if prev else None,
        previous_submission_id=prev[1] if prev else None,
        previous_evidence_id=prev[2] if prev else None,
    )
    rec = info.compute_recommendation()

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
        f"Platform prev: "
        + (f"{info.previous_platform_wape:.5f} ({info.previous_evidence_id})"
           if info.previous_platform_wape is not None else "none"),
        "=" * 60,
    ]
    block = "\n".join(lines)
    print(block)
    return block
```

### Интеграция в `ml/scripts/make_submission.py`

После `write_manifest()`:

```python
from transit_ai.submission.candidate import print_candidate

print_candidate(
    csv_path=output,
    manifest_path=manifest_path,
    model_id=args.model_id,
    submission_id=submission_id,
    holdout_wape=metrics_after["wape_score"],
    submission_start=args.start_date,
    submission_end=args.end_date,
    row_count=len(grid),
    total_predictions=float(grid["prediction"].sum()),
    expected_rows=expected_rows,
)
```

### Тесты `ml/tests/test_candidate.py`

```python
"""Tests for SUBMISSION CANDIDATE helper (T-149)."""
import io
import json
import sys
from pathlib import Path

import pytest

from transit_ai.submission.candidate import (
    CandidateInfo,
    Recommendation,
    print_candidate,
)


def test_recommendation_ready_to_upload_no_previous() -> None:
    """Первый submission — READY_TO_UPLOAD."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"), manifest_path=Path("/tmp/x.json"),
        model_id="x", submission_id="v1", holdout_wape=0.5,
        submission_start="2025-11-01", submission_end="2025-12-31",
        row_count=14640, total_predictions=1e7,
    )
    assert info.compute_recommendation() == Recommendation.READY_TO_UPLOAD


def test_recommendation_ready_to_upload_better() -> None:
    """WAPE выросла относительно предыдущей → READY."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"), manifest_path=Path("/tmp/x.json"),
        model_id="x", submission_id="v2", holdout_wape=0.78,
        submission_start="2025-11-01", submission_end="2025-12-31",
        row_count=14640, total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    assert info.compute_recommendation() == Recommendation.READY_TO_UPLOAD


def test_recommendation_worse_than_previous() -> None:
    """WAPE упала >0.5pp → WORSE."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"), manifest_path=Path("/tmp/x.json"),
        model_id="x", submission_id="v2", holdout_wape=0.70,
        submission_start="2025-11-01", submission_end="2025-12-31",
        row_count=14640, total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    assert info.compute_recommendation() == Recommendation.WORSE_THAN_PREVIOUS


def test_recommendation_identical() -> None:
    """WAPE не изменилась значимо (delta < 0.005) → IDENTICAL."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"), manifest_path=Path("/tmp/x.json"),
        model_id="x", submission_id="v2", holdout_wape=0.7325,
        submission_start="2025-11-01", submission_end="2025-12-31",
        row_count=14640, total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    assert info.compute_recommendation() == Recommendation.IDENTICAL_TO_PREVIOUS


def test_recommendation_needs_fix_on_row_count_mismatch() -> None:
    """row_count != expected_rows → NEEDS_FIX."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"), manifest_path=Path("/tmp/x.json"),
        model_id="x", submission_id="v2", holdout_wape=0.8,
        submission_start="2025-11-01", submission_end="2025-12-31",
        row_count=100, total_predictions=1e6, expected_rows=14640,
    )
    assert info.compute_recommendation() == Recommendation.NEEDS_FIX


def test_print_candidate_format(capsys, tmp_path: Path) -> None:
    """Блок содержит обязательные строки (R2 clinerule 24)."""
    csv = tmp_path / "x.csv"
    csv.write_text("h")
    manifest = tmp_path / "x.json"
    manifest.write_text("{}")
    block = print_candidate(
        csv_path=csv, manifest_path=manifest,
        model_id="x", submission_id="v1", holdout_wape=0.5,
        submission_start="2025-11-01", submission_end="2025-12-31",
        row_count=14640, total_predictions=1e7,
    )
    required = ["SUBMISSION CANDIDATE", "CSV:", "Manifest:", "Model:",
                "Holdout WAPE:", "Date range:", "Rows:", "Total preds:",
                "Recommendation:", "Platform prev:"]
    for line in required:
        assert line in block, f"missing {line!r} in block"
    # Должен быть напечатан в stdout
    captured = capsys.readouterr()
    assert "SUBMISSION CANDIDATE" in captured.out
```

## Cross-references

- Clinerule 24: `.clinerules/24-ml-candidate-output.md`
- T-149: ticket
- T-148a: clinerule 23 (manifest.json)
- F-021: original finding
