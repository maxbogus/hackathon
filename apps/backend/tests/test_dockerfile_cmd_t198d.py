"""Tests for T-198d: Docker CMD/entrypoint использует абсолютные пути.

F-090: backend container падает с
  "exec: apps/backend/scripts/entrypoint.sh: no such file or directory"
потому что WORKDIR=/ и CMD использует относительный путь.
Решение: WORKDIR /app + абсолютный путь в CMD.

F-091: harvester/ml-pipeline CMD с обратными слэшами переносами строк
  не парсится в Dockerfile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _get_dockerfile(package: str) -> Path | None:
    """Возвращает Path к Dockerfile, поддерживает оба варианта имён."""
    for dirname in [package, package.replace("_", "-")]:
        p = REPO_ROOT / "apps" / dirname / "Dockerfile"
        if p.exists():
            return p
    return None


class TestDockerfileCmdPaths:
    """Dockerfile CMD должен использовать абсолютные пути или WORKDIR."""

    def test_backend_dockerfile_uses_absolute_path_for_entrypoint(self) -> None:
        """backend Dockerfile CMD должен указывать на entrypoint.sh с абсолютным путём."""
        path = REPO_ROOT / "apps" / "backend" / "Dockerfile"
        content = path.read_text()
        absolute_marker = '["/app/apps/backend/scripts/entrypoint.sh"'
        has_absolute_path = absolute_marker in content
        has_workdir = "WORKDIR /app" in content
        has_relative_path = 'CMD ["apps/backend/scripts/entrypoint.sh"]' in content
        assert has_absolute_path or (has_workdir and not has_relative_path), (
            "apps/backend/Dockerfile: нужен абсолютный путь к entrypoint.sh "
            "или WORKDIR /app. Относительный путь ломает запуск."
        )

    @pytest.mark.parametrize("package", ["harvester", "ml_pipeline"])
    def test_celery_dockerfile_cmd_single_line(self, package: str) -> None:
        """harvester/ml-pipeline CMD с uv run celery — одна строка без бэкслэшей."""
        path = _get_dockerfile(package)
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        cmd_lines = [
            line for line in content.splitlines() if line.strip().startswith("CMD")
        ]
        assert cmd_lines, f"apps/{package}/Dockerfile не имеет CMD"
        for line in cmd_lines:
            # Не должно быть переносов строк через обратный слэш
            assert "\\\n" not in line, (
                "apps/" + package + "/Dockerfile CMD содержит \\\n — "
                "не парсится в Dockerfile"
            )


class TestDockerfileWorkdir:
    """Каждый Dockerfile должен устанавливать WORKDIR явно."""

    @pytest.mark.parametrize("package", ["backend", "harvester", "ml_pipeline"])
    def test_dockerfile_sets_workdir(self, package: str) -> None:
        """Dockerfile должен явно установить WORKDIR."""
        path = _get_dockerfile(package)
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        has_workdir_app = "WORKDIR /app" in content
        assert has_workdir_app, (
            f"apps/{package}/Dockerfile должен установить WORKDIR /app "
            f"(по умолчанию /, ломает CMD с относительными путями)"
        )
