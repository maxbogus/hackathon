"""Tests for T-198i: backend Dockerfile копирует alembic файлы.

F-092: backend container упал с 'No script_location key found in configuration'.
Причина: Dockerfile скопировал apps/backend/{app,scripts,pyproject.toml},
но забыл apps/backend/alembic.ini + apps/backend/alembic/.
Решение: добавить оба COPY в Dockerfile + RED-тест.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestBackendDockerfileCopiesAlembic:
    """backend Dockerfile должен копировать alembic.ini + alembic/."""

    def test_backend_dockerfile_copies_alembic_ini(self) -> None:
        path = REPO_ROOT / "apps" / "backend" / "Dockerfile"
        content = path.read_text()
        assert "alembic.ini" in content, (
            "apps/backend/Dockerfile должен COPY alembic.ini "
            "(без него `alembic upgrade head` падает с "
            "'No script_location key found in configuration')"
        )

    def test_backend_dockerfile_copies_alembic_dir(self) -> None:
        path = REPO_ROOT / "apps" / "backend" / "Dockerfile"
        content = path.read_text()
        # Ищем COPY с alembic (как директория)
        assert (
            "apps/backend/alembic " in content or "apps/backend/alembic/" in content
        ), (
            "apps/backend/Dockerfile должен COPY apps/backend/alembic/ "
            "(директория с versions/)"
        )

    def test_backend_dockerfile_copies_entrypoint_sh(self) -> None:
        path = REPO_ROOT / "apps" / "backend" / "Dockerfile"
        content = path.read_text()
        assert "apps/backend/scripts/entrypoint.sh" in content, (
            "apps/backend/Dockerfile должен COPY apps/backend/scripts/ "
            "(включая entrypoint.sh)"
        )
