"""Tests for SUBMISSION CANDIDATE helper (T-149, clinerule 24)."""

from __future__ import annotations

import json
from pathlib import Path

from transit_ai.submission.candidate import (
    CandidateInfo,
    Recommendation,
    _find_previous_submission,
    print_candidate,
)

# ----- Recommendation enum --------------------------------------------------


def test_recommendation_ready_to_upload_no_previous() -> None:
    """Первый submission (нет previous) — READY_TO_UPLOAD."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"),
        manifest_path=Path("/tmp/x.json"),
        model_id="x",
        submission_id="v1",
        holdout_wape=0.5,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
    )
    assert info.compute_recommendation() == Recommendation.READY_TO_UPLOAD


def test_recommendation_ready_to_upload_better() -> None:
    """holdout WAPE выросла >0.5pp относительно предыдущей — READY."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"),
        manifest_path=Path("/tmp/x.json"),
        model_id="x",
        submission_id="v2",
        holdout_wape=0.78,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    assert info.compute_recommendation() == Recommendation.READY_TO_UPLOAD


def test_recommendation_worse_than_previous() -> None:
    """holdout WAPE упала >0.5pp — WORSE."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"),
        manifest_path=Path("/tmp/x.json"),
        model_id="x",
        submission_id="v2",
        holdout_wape=0.70,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    assert info.compute_recommendation() == Recommendation.WORSE_THAN_PREVIOUS


def test_recommendation_identical_to_previous() -> None:
    """delta < 0.5pp — IDENTICAL (F-022 пример: calendar не помог)."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"),
        manifest_path=Path("/tmp/x.json"),
        model_id="x",
        submission_id="v2",
        holdout_wape=0.7325,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    assert info.compute_recommendation() == Recommendation.IDENTICAL_TO_PREVIOUS


def test_recommendation_needs_fix_on_row_count_mismatch() -> None:
    """row_count != expected_rows — NEEDS_FIX (R3)."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"),
        manifest_path=Path("/tmp/x.json"),
        model_id="x",
        submission_id="v2",
        holdout_wape=0.8,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=100,
        total_predictions=1e6,
        expected_rows=14640,
    )
    assert info.compute_recommendation() == Recommendation.NEEDS_FIX


def test_recommendation_threshold_boundary() -> None:
    """delta == 0.005 (ровно threshold) → IDENTICAL."""
    info = CandidateInfo(
        csv_path=Path("/tmp/x.csv"),
        manifest_path=Path("/tmp/x.json"),
        model_id="x",
        submission_id="v2",
        holdout_wape=0.73731,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        previous_platform_wape=0.73231,
    )
    # |0.73731 - 0.73231| = 0.005 — ровно threshold, abs < DELTA_THRESHOLD = False
    assert info.compute_recommendation() == Recommendation.READY_TO_UPLOAD


# ----- _find_previous_submission() ------------------------------------------


def test_find_previous_returns_none_on_empty_dir(tmp_path: Path) -> None:
    """Нет predictions/ — None."""
    assert _find_previous_submission(tmp_path) is None


def test_find_previous_returns_none_when_no_submitted(tmp_path: Path) -> None:
    """Есть json без platform_submitted — None."""
    (tmp_path / "no_submit.json").write_text(
        json.dumps({"submission_id": "v1", "platform_submitted": False})
    )
    assert _find_previous_submission(tmp_path) is None


def test_find_previous_picks_newest_submitted(tmp_path: Path) -> None:
    """Выбирает manifest с самым новым mtime + platform_submitted=true."""
    old = tmp_path / "old.json"
    old.write_text(
        json.dumps(
            {
                "submission_id": "old",
                "platform_submitted": True,
                "platform_score": 0.5,
            }
        )
    )
    new = tmp_path / "new.json"
    new.write_text(
        json.dumps(
            {
                "submission_id": "new",
                "platform_submitted": True,
                "platform_score": 0.73231,
            }
        )
    )
    # touch чтобы mtime точно был разный
    import os
    import time

    os.utime(old, (time.time() - 100, time.time() - 100))
    os.utime(new, (time.time(), time.time()))

    result = _find_previous_submission(tmp_path)
    assert result is not None
    score, sub_id, ev_id = result
    assert score == 0.73231
    assert sub_id == "new"
    assert ev_id == "new"


# ----- print_candidate() format ---------------------------------------------


def test_print_candidate_contains_required_lines(tmp_path: Path) -> None:
    """Блок содержит обязательные заголовки (R2 clinerule 24)."""
    csv = tmp_path / "submission_x_v1_20251101_20251231_20260925T1845Z.csv"
    csv.write_text("h")
    manifest = tmp_path / "submission_x_v1_20251101_20251231_20260925T1845Z.json"
    manifest.write_text("{}")

    block = print_candidate(
        csv_path=csv,
        manifest_path=manifest,
        model_id="xgboost_v2",
        submission_id="v5-xgboost",
        holdout_wape=0.8123,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=13_500_000.0,
        predictions_dir=tmp_path,
    )

    required = [
        "=" * 60,
        "SUBMISSION CANDIDATE",
        "CSV:",
        "Manifest:",
        "Model:",
        "Submission ID:",
        "Holdout WAPE:",
        "Date range:",
        "Rows:",
        "Total preds:",
        "Recommendation:",
        "Platform prev:",
    ]
    for line in required:
        assert line in block, f"missing {line!r} in block"


def test_print_candidate_prints_to_stdout(tmp_path: Path, capsys) -> None:
    """Блок напечатан в stdout (R1)."""
    csv = tmp_path / "x.csv"
    csv.write_text("h")
    manifest = tmp_path / "x.json"
    manifest.write_text("{}")
    print_candidate(
        csv_path=csv,
        manifest_path=manifest,
        model_id="x",
        submission_id="v1",
        holdout_wape=0.5,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        predictions_dir=tmp_path,
    )
    captured = capsys.readouterr()
    assert "SUBMISSION CANDIDATE" in captured.out


def test_print_candidate_includes_previous_when_present(tmp_path: Path) -> None:
    """Если есть предыдущий submission, Platform prev содержит WAPE."""
    # previous submitted
    prev = tmp_path / "prev.json"
    prev.write_text(
        json.dumps(
            {
                "submission_id": "v1-bias",
                "platform_submitted": True,
                "platform_score": 0.73231,
            }
        )
    )
    # current
    csv = tmp_path / "current.csv"
    csv.write_text("h")
    manifest = tmp_path / "current.json"
    manifest.write_text("{}")

    block = print_candidate(
        csv_path=csv,
        manifest_path=manifest,
        model_id="x",
        submission_id="v2",
        holdout_wape=0.78,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        predictions_dir=tmp_path,
    )
    assert "0.73231" in block
    assert "v1-bias" in block
    assert "READY_TO_UPLOAD" in block


def test_print_candidate_handles_corrupted_manifest_gracefully(tmp_path: Path) -> None:
    """R5: corrupted json не должен ломать print_candidate."""
    (tmp_path / "bad.json").write_text("not json {{{")
    csv = tmp_path / "x.csv"
    csv.write_text("h")
    manifest = tmp_path / "x.json"
    manifest.write_text("{}")
    # Не должно бросить exception
    block = print_candidate(
        csv_path=csv,
        manifest_path=manifest,
        model_id="x",
        submission_id="v1",
        holdout_wape=0.5,
        submission_start="2025-11-01",
        submission_end="2025-12-31",
        row_count=14640,
        total_predictions=1e7,
        predictions_dir=tmp_path,
    )
    assert "SUBMISSION CANDIDATE" in block
