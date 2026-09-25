"""Tests for make_submission pipeline (T-145)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "ml" / "scripts" / "make_submission.py"

LABELS_DIR = REPO_ROOT / "data" / "real" / "labels"
pytestmark = pytest.mark.skipif(
    not (LABELS_DIR / "labels_day_train.csv").exists(),
    reason="Hackathon labels not present",
)


def _run_submission(
    tmp_path: Path, start: str = "2025-11-01", end: str = "2025-12-31"
) -> Path:
    out = tmp_path / "submission.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--start-date",
            start,
            "--end-date",
            end,
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"make_submission failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    assert out.exists(), f"Output not created: {out}"
    return out


def test_submission_has_14640_rows(tmp_path: Path) -> None:
    out = _run_submission(tmp_path)
    df = pd.read_csv(out, sep=";")
    # 10 routes × 61 days × 24 hours = 14 640
    assert len(df) == 14640, f"Expected 14640, got {len(df)}"


def test_submission_has_correct_columns(tmp_path: Path) -> None:
    out = _run_submission(tmp_path)
    df = pd.read_csv(out, sep=";")
    assert list(df.columns) == ["route", "date", "hour", "prediction"]


def test_submission_covers_all_routes(tmp_path: Path) -> None:
    out = _run_submission(tmp_path)
    df = pd.read_csv(out, sep=";")
    assert set(df["route"].unique()) == {1, 5, 7, 11, 12, 17, 25, 26, 28, 50}


def test_submission_date_range(tmp_path: Path) -> None:
    out = _run_submission(tmp_path)
    df = pd.read_csv(out, sep=";")
    assert df["date"].min() == "2025-11-01"
    assert df["date"].max() == "2025-12-31"


def test_submission_hours_full_grid(tmp_path: Path) -> None:
    out = _run_submission(tmp_path)
    df = pd.read_csv(out, sep=";")
    assert set(df["hour"].unique()) == set(range(24))


def test_submission_predictions_non_negative(tmp_path: Path) -> None:
    out = _run_submission(tmp_path)
    df = pd.read_csv(out, sep=";")
    assert (df["prediction"] >= 0).all()


def test_submission_custom_range(tmp_path: Path) -> None:
    """Свой диапазон: 7 дней → 10 × 7 × 24 = 1680."""
    out = _run_submission(tmp_path, start="2025-12-01", end="2025-12-07")
    df = pd.read_csv(out, sep=";")
    assert len(df) == 1680
    assert df["date"].min() == "2025-12-01"
    assert df["date"].max() == "2025-12-07"


def test_submission_with_coefs(tmp_path: Path) -> None:
    """coef-weather=2.0 → predictions должны быть в 2x больше."""
    out_default = _run_submission(tmp_path, start="2025-12-01", end="2025-12-02")
    df_default = pd.read_csv(out_default, sep=";")

    out_coef = tmp_path / "submission_coef.csv"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--start-date",
            "2025-12-01",
            "--end-date",
            "2025-12-02",
            "--coef-weather",
            "2.0",
            "--output",
            str(out_coef),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    df_coef = pd.read_csv(out_coef, sep=";")
    # Coef 2x → predictions x2 (где default > 0)
    # Допуск 1.0-3.0 для учёта integer rounding (F-042): маленькие predictions
    # округляются до 0/1, после ×2 получаем ratio 0/2 = inf или 1/2 = 0.5
    # Также ratio может быть 1.75 (round(7/4) = 2).
    mask = df_default["prediction"] > 0
    ratio = df_coef[mask]["prediction"] / df_default[mask]["prediction"]
    assert (ratio > 1.9).all() and (ratio < 2.1).all(), f"Ratios: {ratio.unique()[:5]}"
