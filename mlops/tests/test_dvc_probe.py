"""Smoke-тест: DVC probe работает эфемерно через uv run --with dvc.

Сами .dvc-файлы не тестируем — они генерируются dvc-ом. Тестируем:
  1. probe-скрипт существует и исполняемый (для `make dvc-probe`)
  2. uv run --with dvc python -c "import dvc; print(dvc.__version__)" — exit 0
  3. версия dvc >= 3.0

Запуск: make dvc-test (или make mlops-test-full).

ВНИМАНИЕ: тест №2 требует сети при первом резолве пакета (uv --with). В CI без
сети он упадёт — это ожидаемо, поэтому таргет не входит в `make check-all`.
Пути считаются от корня репозитория (parents[2]), а не захардкожены (F-125).
"""

from __future__ import annotations

from pathlib import Path
import shutil
import stat
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DVC_PROBE = REPO_ROOT / "mlops" / "probes" / "dvc_probe.sh"


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


@pytest.mark.skipif(not shutil.which("uv"), reason="uv not installed")
def test_dvc_probe_script_exists() -> None:
    """Probe-скрипт существует и исполняемый (для make dvc-probe)."""
    assert DVC_PROBE.is_file(), f"missing: {DVC_PROBE}"
    mode = DVC_PROBE.stat().st_mode
    assert mode & stat.S_IXUSR, f"not executable: {DVC_PROBE}"


@pytest.mark.skipif(not shutil.which("uv"), reason="uv not installed")
def test_dvc_probe_outputs_version() -> None:
    """uv run --with dvc python -c 'import dvc; print(dvc.__version__)' → exit 0 + version >= 3."""
    result = _run(
        [
            "uv",
            "run",
            "--with",
            "dvc",
            "--directory",
            str(REPO_ROOT),
            "python",
            "-c",
            "import dvc; print(dvc.__version__)",
        ]
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # первая строка stdout — версия
    version_line = result.stdout.strip().split("\n")[0]
    parts = version_line.split(".")
    assert len(parts) >= 2
    major = int(parts[0])
    assert major >= 3, f"dvc version {version_line} too old (need >= 3.0)"
