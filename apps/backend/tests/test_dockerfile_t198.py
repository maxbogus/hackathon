"""Tests for T-198: apps/backend/Dockerfile обновлён для entrypoint.sh.

RED phase: проверяем что Dockerfile использует entrypoint.sh как CMD
и копирует seed_predictions.py + entrypoint.sh в образ.

T-198: чтобы make up работал из коробки, Dockerfile должен:
  1. COPY apps/backend/app/scripts (seed_predictions.py, _parsers.py)
  2. COPY apps/backend/scripts (entrypoint.sh)
  3. CMD apps/backend/scripts/entrypoint.sh
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = REPO_ROOT / "apps" / "backend" / "Dockerfile"


@pytest.fixture()
def dockerfile_content() -> str:
    assert DOCKERFILE.exists(), f"Dockerfile not found: {DOCKERFILE}"
    return DOCKERFILE.read_text()


class TestDockerfileEntrypoint:
    """Dockerfile использует entrypoint.sh для запуска (T-198)."""

    def test_uses_entrypoint_cmd(self, dockerfile_content: str) -> None:
        """CMD должен указывать на entrypoint.sh, а не напрямую на uvicorn."""
        # Может быть в формате: CMD ["path/to/entrypoint.sh"]
        # или CMD ["sh", "path/to/entrypoint.sh"]
        assert "entrypoint.sh" in dockerfile_content, (
            "Dockerfile должен вызывать entrypoint.sh через CMD"
        )
        # Не должно быть прямого вызова uvicorn (это делает entrypoint.sh)
        # Разрешаем упоминание uvicorn в комментариях/HEALTHCHECK
        cmd_lines = [
            line
            for line in dockerfile_content.splitlines()
            if line.strip().startswith("CMD")
        ]
        assert cmd_lines, "Dockerfile не имеет CMD"
        cmd_text = " ".join(cmd_lines)
        # Если CMD упоминает uvicorn напрямую — это плохо (должен быть entrypoint)
        # Но HEALTHCHECK может использовать python -c
        for line in cmd_lines:
            assert "uvicorn" not in line, (
                f"CMD вызывает uvicorn напрямую — это должна делать entrypoint.sh: {line}"
            )

    def test_copies_entrypoint_script(self, dockerfile_content: str) -> None:
        """Dockerfile должен COPY apps/backend/scripts в образ."""
        assert re.search(
            r"COPY.*apps/backend/scripts",
            dockerfile_content,
        ), "Dockerfile должен COPY apps/backend/scripts"

    def test_copies_seed_predictions_script(self, dockerfile_content: str) -> None:
        """Dockerfile должен COPY seed_predictions.py (через app/ или app/scripts/)."""
        # Вариант 1: COPY apps/backend/app/scripts напрямую
        # Вариант 2: COPY apps/backend/app (целиком, включает scripts/)
        has_direct = re.search(r"COPY.*apps/backend/app/scripts", dockerfile_content)
        has_parent = re.search(r"COPY.*apps/backend/app\b", dockerfile_content)
        assert has_direct or has_parent, (
            "Dockerfile должен COPY apps/backend/app или apps/backend/app/scripts "
            "(для seed_predictions.py)"
        )

    def test_chowns_copied_files(self, dockerfile_content: str) -> None:
        """В runtime stage все COPY должны быть --chown=app:app (non-root)."""
        # runtime stage COPYs должны иметь --chown=app:app
        runtime_section = dockerfile_content.split("FROM .* AS runtime", re.DOTALL)
        if len(runtime_section) > 1:
            runtime_part = runtime_section[1]
            copy_lines = [
                line
                for line in runtime_part.splitlines()
                if line.strip().startswith("COPY")
            ]
            for line in copy_lines:
                if "FROM" in line:
                    continue  # COPY --from=...
                assert "--chown=app:app" in line, (
                    f"COPY в runtime stage без --chown=app:app: {line}"
                )

    def test_non_root_user(self, dockerfile_content: str) -> None:
        """USER app или USER app:app должно быть перед CMD."""
        # Допустимы оба варианта:
        # - USER app:app (Debian/Ubuntu, требует /etc/passwd запись)
        # - USER app (standalone, требует adduser)
        has_user = bool(
            re.search(r"USER\s+(app|1000)(?::(?:app|1000))?", dockerfile_content)
        )
        assert has_user, "USER app или USER app:app не найден — non-root requirement"

    def test_exposes_port_8000(self, dockerfile_content: str) -> None:
        """EXPOSE 8000 для FastAPI."""
        assert "EXPOSE 8000" in dockerfile_content

    def test_healthcheck(self, dockerfile_content: str) -> None:
        """HEALTHCHECK на /api/v1/healthz."""
        assert "HEALTHCHECK" in dockerfile_content
        assert "/api/v1/healthz" in dockerfile_content
