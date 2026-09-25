"""Tests for loadtest Makefile targets (T-160).

Validates that make loadtest-* targets exist and use docker compose
with the loadtest profile, as required by R6 hackathon-rules.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = REPO_ROOT / "Makefile"


def _make_help() -> str:
    """Run `make help` and return its output."""
    result = subprocess.run(
        ["make", "help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def _make_dry_run(target: str) -> str:
    """Run `make -n <target>` to inspect the resolved command without executing."""
    result = subprocess.run(
        ["make", "-n", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def test_makefile_exists() -> None:
    assert MAKEFILE.exists(), f"Makefile not found at {MAKEFILE}"


def test_loadtest_smoke_in_help() -> None:
    """make help должен показывать loadtest-smoke target."""
    help_text = _make_help()
    assert "loadtest-smoke" in help_text, "loadtest-smoke target missing from `make help`"


def test_loadtest_smoke_uses_docker_compose() -> None:
    """loadtest-smoke должен использовать docker compose --profile loadtest."""
    dry_run = _make_dry_run("loadtest-smoke")
    assert "docker compose" in dry_run, (
        f"loadtest-smoke must use docker compose. Got: {dry_run[:500]}"
    )
    assert "--profile loadtest" in dry_run, (
        f"loadtest-smoke must use --profile loadtest. Got: {dry_run[:500]}"
    )


def test_loadtest_smoke_uses_k6_script() -> None:
    """loadtest-smoke должен вызывать k6 run с smoke_dispatcher.js."""
    dry_run = _make_dry_run("loadtest-smoke")
    assert "k6" in dry_run, f"loadtest-smoke must invoke k6. Got: {dry_run[:500]}"
    assert "smoke_dispatcher.js" in dry_run, (
        f"loadtest-smoke must reference smoke_dispatcher.js. Got: {dry_run[:500]}"
    )


def test_loadtest_smoke_in_phony() -> None:
    """loadtest-smoke должен быть в .PHONY декларации."""
    makefile_text = MAKEFILE.read_text()
    lines = makefile_text.splitlines()
    # Найти строку начинающуюся с .PHONY:
    phony_start = None
    for i, line in enumerate(lines):
        if line.startswith(".PHONY:"):
            phony_start = i
            break
    assert phony_start is not None, "Makefile missing .PHONY declaration"

    # Собрать блок: текущая строка + все последующие с \
    phony_lines = [lines[phony_start]]
    for i in range(phony_start + 1, len(lines)):
        line = lines[i]
        # Строки-продолжения начинаются с whitespace и заканчиваются на \
        if line.rstrip().endswith("\\"):
            phony_lines.append(line)
        else:
            # Последняя строка блока
            phony_lines.append(line)
            break
    phony_block = "\n".join(phony_lines)
    assert "loadtest-smoke" in phony_block, (
        f"loadtest-smoke missing from .PHONY. Got: {phony_block[:500]}"
    )


def test_loadtest_reports_dir_created() -> None:
    """loadtest-smoke должен создавать каталог reports перед запуском."""
    dry_run = _make_dry_run("loadtest-smoke")
    assert "docs/load-profiles/reports" in dry_run, (
        f"loadtest-smoke must create docs/load-profiles/reports dir. Got: {dry_run[:500]}"
    )
