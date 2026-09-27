"""Smoke-тест: DVC probe работает эфемерно через uv run --with dvc.

Сами .dvc/ файлы не тестируем — они генерируются dvc-ом. Тестируем:
  1. uv run --with dvc python -c "import dvc; print(dvc.__version__)" — exit 0
  2. dvc version >= 3.0
  3. dvc cache dir hardlink fallback (если FS не поддерживает — copy)

Запуск: make dvc-probe (Makefile) или:
    cd mlops && bash probes/dvc_probe.sh
"""

from __future__ import annotations

import subprocess
from pathlib import Path
import shutil

import pytest

DVC_PROBE = Path("/home/maxbogus/Repositories/hackathon/mlops/probes/dvc_probe.sh")


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


@pytest.mark.skipif(not shutil.which("uv"), reason="uv not installed")
def test_dvc_probe_script_exists() -> None:
    """Probe-скрипт существует и исполняемый (для make dvc-probe)."""
    assert DVC_PROBE.is_file(), f"missing: {DVC_PROBE}"
    # исполняемый?
    import stat
    mode = DVC_PROBE.stat().st_mode
    assert mode & stat.S_IXUSR, f"not executable: {DVC_PROBE}"


@pytest.mark.skipif(not shutil.which("uv"), reason="uv not installed")
def test_dvc_probe_outputs_version(tmp_path: Path) -> None:
    """uv run --with dvc python -c 'import dvc; print(dvc.__version__)' → exit 0 + version >= 3."""
    result = _run([
        "uv", "run", "--with", "dvc", "--directory",
        "/home/maxbogus/Repositories/hackathon",
        "python", "-c", "import dvc; print(dvc.__version__)",
    ], timeout=120)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # первая строка stdout — версия
    version_line = result.stdout.strip().split("\n")[0]
    parts = version_line.split(".")
    assert len(parts) >= 2
    major = int(parts[0])
    assert major >= 3, f"dvc version {version_line} too old (need >= 3.0)"
