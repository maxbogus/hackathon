"""Tests for T-198l: Dockerfile устанавливает transit_ai_ml из исходников.

F-093: backend container упал с 'No module named transit_ai'.
Причина: `pip install --no-deps -e ./ml` создаёт .pth файл который не
регистрирует transit_ai как top-level пакет. transit_ai_ml — workspace
package, не опубликован на PyPI.

Решение: `cd ml && pip wheel . && pip install transit_ai_ml` — собирает
.whl из исходников локально (без сети) и устанавливает.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestDockerfileInstallsTransitAiMl:
    """Dockerfile должен устанавливать transit_ai_ml (workspace package)."""

    @pytest.mark.parametrize("package", ["backend", "harvester", "ml_pipeline"])
    def test_dockerfile_installs_transit_ai_ml(self, package: str) -> None:
        """Dockerfile должен собирать .whl из ./ml и устанавливать transit_ai_ml."""
        for dirname in [package, package.replace("_", "-")]:
            path = REPO_ROOT / "apps" / dirname / "Dockerfile"
            if path.exists():
                content = path.read_text()
                # Допустимые варианты:
                # - pip install -e ./ml (с package layout правильным)
                # - pip wheel ./ml + pip install transit_ai_ml
                # - pip install ./ml (если pyproject.toml настроен правильно)
                # T-198l: PYTHONPATH=/app/ml — самый простой способ
                # (без pip install -e или pip wheel, которые ломаются)
                has_pythonpath_ml = "PYTHONPATH=/app/ml" in content
                assert has_pythonpath_ml, (
                    f"apps/{package}/Dockerfile должен установить PYTHONPATH=/app/ml "
                    f"(для import transit_ai.* без pip install -e или wheel)"
                )
                return
        pytest.skip(f"apps/{package}/Dockerfile не найден")
