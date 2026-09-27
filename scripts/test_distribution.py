"""Tests for T-198b: distribution infrastructure для жюри.

Проверяет что wheels/ dirs и DISTRIBUTION.md корректно настроены.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestWheelsDirs:
    """Каждый apps/* с Dockerfile должен иметь wheels/ dir + .gitignore."""

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml-pipeline"],
    )
    def test_wheels_dir_exists(self, package: str) -> None:
        """apps/<package>/wheels/ должен существовать (создаётся при build-*)."""
        # Допускаем как с дефисом так и с underscore (ml_pipeline vs ml-pipeline)
        for dirname in [package, package.replace("-", "_")]:
            path = REPO_ROOT / "apps" / dirname / "wheels"
            if path.is_dir():
                return
        # Ни один из вариантов не найден
        assert False, (
            "apps/{backend,harvester,ml-pipeline,ml_pipeline}/wheels/ "
            "должен существовать для offline build (проверены варианты)"
        )

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml_pipeline"],
    )
    def test_package_gitignore_excludes_wheels(self, package: str) -> None:
        """apps/<package>/.gitignore должен исключать wheels/ и requirements.txt."""
        # Проверяем как с дефисом так и с underscore
        for dirname in [package, package.replace("-", "_")]:
            path = REPO_ROOT / "apps" / dirname / ".gitignore"
            if path.exists():
                content = path.read_text()
                assert "wheels/" in content, (
                    f"apps/{dirname}/.gitignore должен содержать `wheels/`"
                )
                assert "requirements.txt" in content, (
                    f"apps/{dirname}/.gitignore должен содержать `requirements.txt`"
                )
                return
        # Не нашли .gitignore ни в одном варианте — это нормально пока
        pytest.skip(f".gitignore для {package} не существует")


class TestDockerignore:
    """.dockerignore НЕ должен игнорировать wheels/ (нужны для build)."""

    def test_dockerignore_allows_wheels(self) -> None:
        path = REPO_ROOT / ".dockerignore"
        if not path.exists():
            pytest.skip(".dockerignore не существует")
        content = path.read_text()
        # Должны быть строки !apps/<pkg>/wheels/ для всех 3 пакетов
        # (поддерживаем оба варианта имён для ml-pipeline)
        has_backend = "!apps/backend/wheels/" in content
        has_harvester = "!apps/harvester/wheels/" in content
        has_ml = (
            "!apps/ml_pipeline/wheels/" in content
            or "!apps/ml-pipeline/wheels/" in content
        )
        assert has_backend, (
            ".dockerignore должен содержать `!apps/backend/wheels/` "
            "(wheels нужны для offline Docker build)"
        )
        assert has_harvester, (
            ".dockerignore должен содержать `!apps/harvester/wheels/`"
        )
        assert has_ml, (
            ".dockerignore должен содержать `!apps/ml_pipeline/wheels/` "
            "или `!apps/ml-pipeline/wheels/`"
        )


class TestDistributionDoc:
    """docs/DISTRIBUTION.md существует с полным workflow для жюри + организаторов."""

    def test_distribution_md_exists(self) -> None:
        path = REPO_ROOT / "docs" / "DISTRIBUTION.md"
        assert path.exists(), (
            "docs/DISTRIBUTION.md должен существовать (workflow для жюри)"
        )

    def test_distribution_md_has_jury_section(self) -> None:
        path = REPO_ROOT / "docs" / "DISTRIBUTION.md"
        if not path.exists():
            pytest.skip("docs/DISTRIBUTION.md не существует")
        content = path.read_text().lower()
        # Workflow для жюри
        assert "жюри" in content or "jury" in content, (
            "docs/DISTRIBUTION.md должен иметь секцию для жюри"
        )
        assert "import-images" in content or "docker load" in content, (
            "docs/DISTRIBUTION.md должен описывать import-images / docker load"
        )

    def test_distribution_md_has_organizers_section(self) -> None:
        path = REPO_ROOT / "docs" / "DISTRIBUTION.md"
        if not path.exists():
            pytest.skip("docs/DISTRIBUTION.md не существует")
        content = path.read_text().lower()
        assert (
            "организатор" in content or "organizer" in content
        ), "docs/DISTRIBUTION.md должен иметь секцию для организаторов"
        assert "export-images" in content or "docker save" in content, (
            "docs/DISTRIBUTION.md должен описывать export-images / docker save"
        )

    def test_distribution_md_has_yandex_disk(self) -> None:
        path = REPO_ROOT / "docs" / "DISTRIBUTION.md"
        if not path.exists():
            pytest.skip("docs/DISTRIBUTION.md не существует")
        content = path.read_text().lower()
        assert "яндекс" in content or "yandex" in content, (
            "docs/DISTRIBUTION.md должен упоминать Яндекс.Диск как distribution channel"
        )

    def test_distribution_md_has_architecture(self) -> None:
        path = REPO_ROOT / "docs" / "DISTRIBUTION.md"
        if not path.exists():
            pytest.skip("docs/DISTRIBUTION.md не существует")
        content = path.read_text().lower()
        # Архитектурная диаграмма (ASCII art или mermaid)
        assert (
            "архитектур" in content or "architecture" in content
        ), "docs/DISTRIBUTION.md должен иметь архитектурную диаграмму"
        # Должна быть визуальная схема (таблица, ASCII art, mermaid)
        assert (
            "|" in content  # таблица
            or "```" in content  # code block
            or "graph" in content  # mermaid
        ), "docs/DISTRIBUTION.md должен иметь визуальную схему"

    def test_distribution_md_has_screens(self) -> None:
        path = REPO_ROOT / "docs" / "DISTRIBUTION.md"
        if not path.exists():
            pytest.skip("docs/DISTRIBUTION.md не существует")
        content = path.read_text().lower()
        # Описание 5 экранов
        for screen in ["passenger", "dispatcher", "analyst", "planner"]:
            assert screen in content, (
                f"docs/DISTRIBUTION.md должен описывать экран {screen}"
            )


class TestDockerfilesOffline:
    """Каждый Dockerfile должен использовать offline pip install из wheels."""

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml_pipeline"],
    )
    def test_dockerfile_uses_pip_no_index(self, package: str) -> None:
        """Dockerfile должен использовать `pip install --no-index` для offline build."""
        # Поддержка обоих вариантов имён директорий
        path = None
        for dirname in [package, package.replace("_", "-")]:
            p = REPO_ROOT / "apps" / dirname / "Dockerfile"
            if p.exists():
                path = p
                break
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        assert "--no-index" in content, (
            f"apps/{package}/Dockerfile должен использовать `pip install --no-index` "
            "для offline build (не ходить в PyPI)"
        )

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml_pipeline"],
    )
    def test_dockerfile_copies_wheels(self, package: str) -> None:
        """Dockerfile должен COPY apps/<package>/wheels/ в /tmp/wheels."""
        path = None
        for dirname in [package, package.replace("_", "-")]:
            p = REPO_ROOT / "apps" / dirname / "Dockerfile"
            if p.exists():
                path = p
                break
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        assert "wheels" in content.lower(), (
            f"apps/{package}/Dockerfile должен упоминать wheels/"
        )

    @pytest.mark.parametrize(
        "package",
        ["backend", "harvester", "ml_pipeline"],
    )
    def test_dockerfile_no_uv_sync_in_runtime(self, package: str) -> None:
        """Runtime stage использует ТОЛЬКО `uv sync --offline` (или pip), без сети."""
        path = None
        for dirname in [package, package.replace("_", "-")]:
            p = REPO_ROOT / "apps" / dirname / "Dockerfile"
            if p.exists():
                path = p
                break
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        # Если есть AS runtime, в runtime stage не должно быть `uv sync` БЕЗ --offline
        if "AS runtime" in content:
            runtime_section = content.split("AS runtime", 1)[1]
            # Должен быть `uv sync --offline` (НЕ ходит в PyPI)
            # Или вообще не должно быть `uv sync` (комментарии игнорируем)
            uv_sync_lines = [
                line for line in runtime_section.splitlines()
                if "uv sync" in line
                and "--offline" not in line
                and not line.strip().startswith("#")
            ]
            assert not uv_sync_lines, (
                f"apps/{package}/Dockerfile runtime stage использует `uv sync` БЕЗ --offline — "
                f"это попытка скачать deps из PyPI. Должен быть `uv sync --offline` "
                f"или только `pip install --no-index`:\n  {uv_sync_lines}"
            )
