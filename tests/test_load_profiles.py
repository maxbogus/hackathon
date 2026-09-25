"""Tests for k6 load profiles (T-162).

Validates that the 4 load profiles (baseline/stress/spike/soak) exist as
separate JS scripts in tests/load/, each with profile-specific stages
and thresholds, and that each is invoked by the corresponding make target.

R6 hackathon-rules + docs/load-profiles/README.md contract.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LOAD_DIR = REPO_ROOT / "tests" / "load"
MAKEFILE = REPO_ROOT / "Makefile"

# Профили и их канонические параметры
PROFILES: dict[str, dict[str, object]] = {
    "baseline": {"vus": 50, "duration": "5m", "p95": 2000, "err": 0.01, "stages": False},
    "stress": {"vus": 100, "duration": "3m", "p95": 3000, "err": 0.02, "stages": True},
    "spike": {"vus": 200, "duration": "3m", "p95": 4000, "err": 0.02, "stages": True},
    "soak": {"vus": 30, "duration": "30m", "p95": 2000, "err": 0.005, "stages": False},
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _make_dry_run(target: str) -> str:
    result = subprocess.run(
        ["make", "-n", target],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def _make_phony_block() -> str:
    """Собрать .PHONY блок (с учётом многострочных \\ продолжений)."""
    text = _read(MAKEFILE)
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(".PHONY:"):
            start = i
            break
    assert start is not None, "Makefile missing .PHONY declaration"
    block: list[str] = [lines[start]]
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if line.rstrip().endswith("\\"):
            block.append(line)
        else:
            block.append(line)
            break
    return "\n".join(block)


# === JS-скрипты: наличие и валидность ===


@pytest.mark.parametrize("profile", list(PROFILES.keys()))
def test_profile_script_exists(profile: str) -> None:
    """Каждый профиль должен иметь свой JS-скрипт в tests/load/."""
    script = LOAD_DIR / f"{profile}_dispatcher.js"
    assert script.exists(), f"Missing k6 script: {script}"


@pytest.mark.parametrize("profile", list(PROFILES.keys()))
def test_profile_script_imports_k6(profile: str) -> None:
    """Каждый скрипт должен импортировать k6/http и k6/metrics."""
    text = _read(LOAD_DIR / f"{profile}_dispatcher.js")
    assert "from 'k6/http'" in text, f"{profile}: missing k6/http import"
    assert "from 'k6/metrics'" in text, f"{profile}: missing k6/metrics import"


@pytest.mark.parametrize("profile", list(PROFILES.keys()))
def test_profile_script_has_thresholds(profile: str) -> None:
    """Каждый скрипт должен содержать thresholds с p95 и error_rate."""
    cfg = PROFILES[profile]
    text = _read(LOAD_DIR / f"{profile}_dispatcher.js")
    p95 = cfg["p95"]
    err = cfg["err"]
    assert re.search(rf"p\(95\)<{p95}", text), f"{profile}: missing threshold p(95)<{p95}"
    err_str = f"rate<{err}"
    assert err_str in text, f"{profile}: missing threshold {err_str}"


@pytest.mark.parametrize("profile", list(PROFILES.keys()))
def test_profile_script_uses_stages(profile: str) -> None:
    """Профили stress и spike обязаны использовать stages."""
    cfg = PROFILES[profile]
    text = _read(LOAD_DIR / f"{profile}_dispatcher.js")
    if cfg["stages"]:
        assert "stages:" in text, f"{profile}: required to use stages"
        stage_count = text.count("duration:")
        assert stage_count >= 3, (
            f"{profile}: need ≥3 stages (ramp-up + hold + ramp-down). Got: {stage_count}"
        )


@pytest.mark.parametrize("profile", ["baseline", "stress"])
def test_profile_script_round_robin_endpoints(profile: str) -> None:
    """Baseline и stress должны покрывать 3 эндпоинта (round-robin)."""
    text = _read(LOAD_DIR / f"{profile}_dispatcher.js")
    assert "/api/v1/predictions/stop/" in text, f"{profile}: missing /api/v1/predictions/stop/"
    assert "/api/v1/predictions/eta" in text, f"{profile}: missing /api/v1/predictions/eta"
    assert "/api/v1/models/active" in text, f"{profile}: missing /api/v1/models/active"


# === Makefile targets ===


@pytest.mark.parametrize("profile", list(PROFILES.keys()))
def test_makefile_target_calls_profile_script(profile: str) -> None:
    """make loadtest-<profile> должен вызывать <profile>_dispatcher.js."""
    target = f"loadtest-{profile}"
    dry_run = _make_dry_run(target)
    expected_script = f"{profile}_dispatcher.js"
    assert expected_script in dry_run, (
        f"{target}: must call {expected_script}. Got: {dry_run[:500]}"
    )


@pytest.mark.parametrize("profile", list(PROFILES.keys()))
def test_makefile_target_in_phony(profile: str) -> None:
    """Каждый loadtest-<profile> target должен быть в .PHONY."""
    target = f"loadtest-{profile}"
    block = _make_phony_block()
    assert target in block, f"{target} missing from .PHONY"


def test_makefile_target_in_help() -> None:
    """make help должен показывать все 4 профиля."""
    help_text = subprocess.run(
        ["make", "help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    for profile in PROFILES:
        assert f"loadtest-{profile}" in help_text, f"loadtest-{profile} missing from `make help`"


def test_loadtest_all_runs_all_profiles_except_soak() -> None:
    """loadtest-all: smoke + baseline + stress + spike (без soak)."""
    dry_run = _make_dry_run("loadtest-all")
    for profile in ("smoke", "baseline", "stress", "spike"):
        assert profile in dry_run, f"loadtest-all must include {profile}. Got: {dry_run[:1000]}"


# === Документация ===


def test_load_profiles_readme_exists() -> None:
    """docs/load-profiles/README.md должен существовать."""
    readme = REPO_ROOT / "docs" / "load-profiles" / "README.md"
    assert readme.exists(), "Missing docs/load-profiles/README.md"


def test_load_profiles_readme_documents_all_profiles() -> None:
    """README должен упоминать все 5 профилей (smoke + 4 новых)."""
    readme = REPO_ROOT / "docs" / "load-profiles" / "README.md"
    text = _read(readme)
    for profile in ("smoke", "baseline", "stress", "spike", "soak"):
        assert profile in text, f"README.md missing profile: {profile}"


def test_load_profiles_readme_has_interpretation() -> None:
    """README должен содержать раздел интерпретации графиков."""
    readme = REPO_ROOT / "docs" / "load-profiles" / "README.md"
    text = _read(readme)
    assert "Latency" in text or "latency" in text, "README: missing latency interpretation"
    assert "RPS" in text or "Requests" in text, "README: missing RPS section"


def test_spike_has_10_to_200_ramp() -> None:
    """Spike: 10 VU → 200 VU (резкий скачок)."""
    text = _read(LOAD_DIR / "spike_dispatcher.js")
    targets = re.findall(r"target:\s*(\d+)", text)
    targets_int = [int(t) for t in targets]
    assert 10 in targets_int, f"spike: missing 10 VU baseline. Got: {targets_int}"
    assert 200 in targets_int, f"spike: missing 200 VU spike. Got: {targets_int}"
