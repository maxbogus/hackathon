"""Tests for scripts/check_training_time.py (T-165)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_training_time.py"


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, check=False)


def _make_artifact(artifacts_dir: Path, model_id: str, train_time_sec: float) -> Path:
    """Create a fake model artifact directory with meta.json."""
    model_dir = artifacts_dir / model_id
    model_dir.mkdir(parents=True, exist_ok=True)
    meta = {"model_id": model_id, "train_time_sec": train_time_sec}
    (model_dir / "meta.json").write_text(json.dumps(meta))
    return model_dir


def test_script_exists() -> None:
    assert SCRIPT.exists()


def test_pass_when_total_below_60_min(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _make_artifact(artifacts, "model_a", 1200.0)  # 20 min
    _make_artifact(artifacts, "model_b", 1500.0)  # 25 min
    # Total = 45 min
    result = _run_script("--artifacts-dir", str(artifacts))
    assert result.returncode == 0, f"Expected PASS: {result.stdout}\n{result.stderr}"
    assert "R6 PASS" in result.stdout


def test_fail_when_total_above_60_min(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _make_artifact(artifacts, "big_model", 4500.0)  # 75 min
    result = _run_script("--artifacts-dir", str(artifacts))
    assert result.returncode == 1, f"Expected FAIL: {result.stdout}"
    assert "R6 breach" in result.stdout


def test_pass_when_artifacts_dir_empty(tmp_path: Path) -> None:
    artifacts = tmp_path / "empty"
    artifacts.mkdir()
    result = _run_script("--artifacts-dir", str(artifacts))
    assert result.returncode == 0
    assert "No artifacts found" in result.stdout


def test_skip_broken_meta_json(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _make_artifact(artifacts, "good", 100.0)
    # Broken meta
    bad = artifacts / "bad_model"
    bad.mkdir()
    (bad / "meta.json").write_text("not json {{{")
    result = _run_script("--artifacts-dir", str(artifacts))
    # Должен warning, но продолжить и PASS
    assert result.returncode == 0
    assert "WARNING" in result.stderr or "skipping" in result.stderr


def test_custom_limit_via_cli(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _make_artifact(artifacts, "small", 700.0)  # ~12 min
    # С limit 600s — должен fail
    result = _run_script("--artifacts-dir", str(artifacts), "--limit-sec", "600")
    assert result.returncode == 1
    assert "R6 breach" in result.stdout


def test_default_limit_is_3600() -> None:
    """R6 hackathon-rules: 60 min = 3600 sec."""
    # Прочитать default из argparse help
    result = _run_script("--help")
    assert "3600" in result.stdout, f"Default 3600s should be in help: {result.stdout}"


def test_multiple_models_aggregated(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _make_artifact(artifacts, "a", 600.0)
    _make_artifact(artifacts, "b", 600.0)
    _make_artifact(artifacts, "c", 600.0)
    # Total = 1800s = 30 min, OK
    result = _run_script("--artifacts-dir", str(artifacts))
    assert result.returncode == 0
    assert "30.00" in result.stdout or "30.0" in result.stdout


def test_table_format(tmp_path: Path) -> None:
    """Output должен быть в табличном формате."""
    artifacts = tmp_path / "artifacts"
    _make_artifact(artifacts, "model_x", 120.0)
    result = _run_script("--artifacts-dir", str(artifacts))
    assert "Model ID" in result.stdout
    assert "Time (sec)" in result.stdout
    assert "Time (min)" in result.stdout
    assert "TOTAL" in result.stdout
