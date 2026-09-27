"""Тесты make-таргетов external ETL (шаг 0, T-231).

Проверяют, что `make external-*` объявлены, запускают `app.build` через uv
и что `pipeline-fetch` больше не WIP-заглушка.

Запуск: make test-root
"""

from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]

EXTERNAL_TARGETS = ("external-gen", "external-verify", "external-show", "external-all")


def _make_dry_run(target: str) -> str:
    result = subprocess.run(
        ["make", "-n", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout + result.stderr


def _make_help() -> str:
    result = subprocess.run(
        ["make", "help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def test_external_targets_are_declared() -> None:
    help_text = _make_help()
    for target in EXTERNAL_TARGETS:
        assert target in help_text, f"{target} отсутствует в make help"


def test_external_gen_runs_app_build_via_uv() -> None:
    output = _make_dry_run("external-gen")
    assert "app.build" in output, output
    assert "uv" in output, output


def test_external_verify_target_checks_manifest() -> None:
    output = _make_dry_run("external-verify")
    assert "--verify" in output, output


def test_pipeline_fetch_is_not_wip() -> None:
    """pipeline-fetch должен быть рабочим (не [WIP]) и звать ETL (app.build)."""
    help_text = _make_help()
    for line in help_text.splitlines():
        if "pipeline-fetch" in line:
            assert "[WIP" not in line, line
    assert "app.build" in _make_dry_run("pipeline-fetch")
