"""Tests for T-198m: Dockerfile копирует ml/transit_ai/ (исходный код workspace).

F-094: backend container упал с 'No module named transit_ai'.
Причина: Dockerfile скопировал только ml/{pyproject.toml,README.md},
но забыл ml/transit_ai/ (исходный код модуля) — без него нет top-level
пакета transit_ai.
Решение: COPY ml/transit_ai /app/ml/transit_ai.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _get_dockerfile(package: str) -> Path | None:
    for dirname in [package, package.replace("_", "-")]:
        p = REPO_ROOT / "apps" / dirname / "Dockerfile"
        if p.exists():
            return p
    return None


class TestDockerfileCopiesTransitAiSource:
    """Dockerfile должен копировать исходный код workspace ml/transit_ai."""

    @pytest.mark.parametrize("package", ["backend", "harvester", "ml_pipeline"])
    def test_dockerfile_copies_ml_transit_ai(self, package: str) -> None:
        path = _get_dockerfile(package)
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        # Должен быть COPY ml/transit_ai (исходный код workspace)
        assert ("ml/transit_ai" in content
                and "COPY" in content), (
            f"apps/{package}/Dockerfile должен COPY ml/transit_ai "
            f"(исходный код workspace, без него нет модуля transit_ai)"
        )
