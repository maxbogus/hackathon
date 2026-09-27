"""Tests for T-198c: Dockerfile filter editable requirements при pip install.

Проблема: uv export содержит `-e ./*` строки (workspace source).
Эти строки ломают `pip install --no-index` в runtime stage.
Решение: фильтровать через grep/sed в Dockerfile ПЕРЕД pip install.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestDockerfileFiltersEditable:
    """Dockerfile должен фильтровать `-e ./*` перед pip install."""

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml_pipeline"],
    )
    def test_dockerfile_filters_editable_requirements(self, package: str) -> None:
        """Dockerfile должен grep -v или sed для удаления editable из requirements."""
        path = None
        for dirname in [package, package.replace("_", "-")]:
            p = REPO_ROOT / "apps" / dirname / "Dockerfile"
            if p.exists():
                path = p
                break
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()

        # Проверяем что есть grep/sed для удаления editable
        # Допустимые варианты:
        # - `grep -v '^-e\.' /tmp/requirements.txt > /tmp/req.deps.txt`
        # - `sed -i '/^-e\./d' /tmp/requirements.txt`
        # - `sed '/^-e\./d' /tmp/requirements.txt > /tmp/req.deps.txt`
        has_grep_filter = (
            "grep -v" in content
            and ("'^-e" in content or '"^-e' in content or "^-e" in content)
        )
        has_sed_filter = (
            "sed" in content
            and ("^-e" in content or "/-e" in content)
        )
        assert has_grep_filter or has_sed_filter, (
            f"apps/{package}/Dockerfile должен отфильтровать editable requirements "
            f"перед `pip install --no-index`. Используй grep -v или sed."
        )

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml_pipeline"],
    )
    def test_dockerfile_uses_filtered_file_for_pip(self, package: str) -> None:
        """pip install должен использовать ОТФИЛЬТРОВАННЫЙ файл (без editable)."""
        path = None
        for dirname in [package, package.replace("_", "-")]:
            p = REPO_ROOT / "apps" / dirname / "Dockerfile"
            if p.exists():
                path = p
                break
        assert path
        content = path.read_text()

        # Должен быть COPY requirements.txt (исходный)
        # + grep/sed → requirements.deps.txt (отфильтрованный)
        # + pip install -r requirements.deps.txt (НЕ -r requirements.txt!)
        #
        # Проверяем что pip install НЕ использует напрямую requirements.txt
        # (без фильтрации)
        # Найти строку с pip install -r
        pip_install_lines = [
            line for line in content.splitlines()
            if "pip install" in line and "-r" in line
        ]
        assert pip_install_lines, (
            f"apps/{package}/Dockerfile должен иметь `pip install -r ...`"
        )
        # Каждая строка pip install должна указывать на .deps.txt (НЕ .txt без суффикса)
        uses_deps_file = any(
            ".deps.txt" in line or "deps.txt" in line
            for line in pip_install_lines
        )
        uses_raw_file = any(
            "-r /tmp/requirements.txt" in line
            for line in pip_install_lines
            if ".deps" not in line
        )
        assert uses_deps_file, (
            f"apps/{package}/Dockerfile pip install должен использовать "
            f"ОТФИЛЬТРОВАННЫЙ requirements.deps.txt, не исходный requirements.txt"
        )
        assert not uses_raw_file, (
            f"apps/{package}/Dockerfile использует НЕотфильтрованный requirements.txt "
            f"в pip install — упадёт с ошибкой editable requirement"
        )
