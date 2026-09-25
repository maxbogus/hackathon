"""Tests for scripts/check_load_sla.py (T-161)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_load_sla.py"


def _run_sla(*args: str, report: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run check_load_sla.py with given args."""
    cmd = [sys.executable, str(SCRIPT), *args]
    if report is not None:
        cmd.append(str(report))
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=REPO_ROOT, check=False
    )


def _make_report(tmp_path: Path, p95: float, error_rate: float) -> Path:
    """Create a fake k6 JSON report file."""
    data = {
        "metrics": {
            "http_req_duration": {
                "values": {
                    "avg": 100.0,
                    "min": 50.0,
                    "max": 500.0,
                    "p(50)": 90.0,
                    "p(95)": p95,
                    "p(99)": p95 * 1.5,
                }
            },
            "http_req_failed": {
                "values": {"rate": error_rate, "passes": int(1000 * (1 - error_rate)), "fails": int(1000 * error_rate)}
            },
            "http_reqs": {"values": {"count": 1000}},
        }
    }
    p = tmp_path / "test_report.json"
    p.write_text(json.dumps(data))
    return p


def test_script_exists() -> None:
    assert SCRIPT.exists()


def test_pass_when_p95_below_2000ms(tmp_path: Path) -> None:
    report = _make_report(tmp_path, p95=1500.0, error_rate=0.005)
    result = _run_sla(report=report)
    assert result.returncode == 0, f"Expected PASS, got: {result.stdout}\n{result.stderr}"
    assert "SLA PASS" in result.stdout


def test_fail_when_p95_above_2000ms(tmp_path: Path) -> None:
    report = _make_report(tmp_path, p95=2500.0, error_rate=0.005)
    result = _run_sla(report=report)
    assert result.returncode == 1, f"Expected FAIL, got: {result.stdout}"
    assert "R6 SLA breach" in result.stdout


def test_fail_when_error_rate_above_1pct(tmp_path: Path) -> None:
    report = _make_report(tmp_path, p95=1500.0, error_rate=0.05)
    result = _run_sla(report=report)
    assert result.returncode == 1, f"Expected FAIL, got: {result.stdout}"
    assert "error_rate" in result.stdout


def test_pass_with_zero_errors(tmp_path: Path) -> None:
    report = _make_report(tmp_path, p95=100.0, error_rate=0.0)
    result = _run_sla(report=report)
    assert result.returncode == 0


def test_custom_p95_threshold(tmp_path: Path) -> None:
    report = _make_report(tmp_path, p95=1500.0, error_rate=0.005)
    # С кастомным threshold 1000ms — должен fail
    result = _run_sla("--p95-ms", "1000", report=report)
    assert result.returncode == 1


def test_custom_error_rate_threshold(tmp_path: Path) -> None:
    report = _make_report(tmp_path, p95=100.0, error_rate=0.005)
    # С кастомным threshold 0.001 — должен fail
    result = _run_sla("--error-rate", "0.001", report=report)
    assert result.returncode == 1


def test_broken_json_exits_nonzero(tmp_path: Path) -> None:
    bad_report = tmp_path / "bad.json"
    bad_report.write_text("not valid json {{{")
    result = _run_sla(report=bad_report)
    assert result.returncode != 0
    assert "Failed to parse" in result.stderr or "parse" in result.stderr.lower()


def test_missing_file_exits_nonzero() -> None:
    result = _run_sla(report=Path("/nonexistent/report.json"))
    assert result.returncode != 0


def test_latest_finds_latest_report(tmp_path: Path) -> None:
    """--latest должен находить самый новый JSON в reports dir."""
    report_dir = tmp_path
    # Создать 2 файла с разным mtime
    old = report_dir / "old.json"
    old.write_text(json.dumps({"metrics": {"http_req_duration": {"values": {"p(95)": 100}}, "http_req_failed": {"values": {"rate": 0}}, "http_reqs": {"values": {"count": 1}}}}))
    time.sleep(0.1)
    new = report_dir / "new.json"
    new.write_text(json.dumps({"metrics": {"http_req_duration": {"values": {"p(95)": 2000}}, "http_req_failed": {"values": {"rate": 0}}, "http_reqs": {"values": {"count": 1}}}}))
    result = _run_sla("--latest", "--reports-dir", str(report_dir))
    # latest — должен быть "new" (p95=2000, на грани)
    assert "Checking SLA" in result.stdout
    assert "new.json" in result.stdout or "p95=2000" in result.stdout


def test_no_reports_exits_nonzero(tmp_path: Path) -> None:
    """Если каталог reports пуст — exit 1."""
    result = _run_sla("--latest", "--reports-dir", str(tmp_path))
    assert result.returncode != 0
