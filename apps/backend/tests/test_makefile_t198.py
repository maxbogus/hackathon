"""Tests for T-198: Makefile targets для комиссии.

Цель: `make up` поднимает ВСЁ (postgres+redis+backend+frontend+harvester+ml-pipeline).
+ `make up-status` — healthchecks для всех сервисов.
+ `make pipeline-full` — Celery full_pipeline task.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE = REPO_ROOT / "Makefile"


@pytest.fixture()
def makefile_content() -> str:
    assert MAKEFILE.exists(), f"Makefile not found: {MAKEFILE}"
    return MAKEFILE.read_text()


class TestMakefileUpTargets:
    """T-198: make up поднимает полный стек."""

    def test_up_target_exists(self, makefile_content: str) -> None:
        assert re.search(r"^up:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `up:`"
        )

    def test_up_uses_dc_up(self, makefile_content: str) -> None:
        """up: target должен использовать $(DC) up -d."""
        # Найти target up: и проверить что есть $(DC) up
        match = re.search(
            r"^up:.*?(?=^[a-zA-Z_-]+:|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "up target не найден"
        target_body = match.group(0)
        assert "$(DC)" in target_body or "docker compose" in target_body.lower(), (
            "up target должен использовать docker compose ($(DC))"
        )
        assert "up" in target_body and "-d" in target_body, (
            "up target должен вызывать `docker compose up -d`"
        )

    def test_up_minimal_target_exists(self, makefile_content: str) -> None:
        """T-198: должен быть target `up-minimal` (без Celery workers)."""
        assert re.search(r"^up-minimal:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `up-minimal:` (без harvester + ml-pipeline)"
        )

    def test_up_status_target_exists(self, makefile_content: str) -> None:
        """T-198: должен быть target `up-status` для проверки healthchecks."""
        assert re.search(r"^up-status:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `up-status:` для healthchecks"
        )


class TestMakefilePipelineTargets:
    """T-198: pipeline-full + pipeline-status."""

    def test_pipeline_full_target_exists(self, makefile_content: str) -> None:
        """pipeline-full должен вызывать Celery ml_pipeline.full_pipeline task."""
        assert re.search(r"^pipeline-full:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `pipeline-full:`"
        )
        match = re.search(
            r"^pipeline-full:.*?(?=^[a-zA-Z_-]+:|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert match
        body = match.group(0)
        assert "full_pipeline" in body, (
            "pipeline-full должен вызывать ml_pipeline.full_pipeline task"
        )

    def test_pipeline_status_target_exists(self, makefile_content: str) -> None:
        """pipeline-status для проверки активных Celery tasks."""
        assert re.search(r"^pipeline-status:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `pipeline-status:`"
        )


class TestMakefileHelp:
    """T-198: новые targets должны быть в make help."""

    def test_help_includes_up_minimal(self, makefile_content: str) -> None:
        assert "up-minimal" in makefile_content

    def test_help_includes_up_status(self, makefile_content: str) -> None:
        assert "up-status" in makefile_content


class TestMakefileBuildTargets:
    """T-198b: pre-build wheels targets (offline dependency cache)."""

    def test_build_backend_target_exists(self, makefile_content: str) -> None:
        """make build-backend создаёт apps/backend/wheels/ для offline build."""
        assert re.search(r"^build-backend:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `build-backend:` для pre-build wheels"
        )

    def test_build_harvester_target_exists(self, makefile_content: str) -> None:
        """make build-harvester для offline build harvester."""
        assert re.search(r"^build-harvester:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `build-harvester:`"
        )

    def test_build_ml_pipeline_target_exists(self, makefile_content: str) -> None:
        """make build-ml-pipeline для offline build ml-pipeline."""
        assert re.search(r"^build-ml-pipeline:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `build-ml-pipeline:`"
        )

    def test_build_all_target_exists(self, makefile_content: str) -> None:
        """make build-all собирает все wheels (зависит от остальных)."""
        assert re.search(r"^build-all:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `build-all:`"
        )

    def test_build_backend_uses_pip_download(self, makefile_content: str) -> None:
        """build-backend должен использовать `pip download` (не `uv pip download`).

        uv НЕ имеет subcommand `download`. Используем `uv run pip download`
        или системный `pip download` через venv.
        """
        match = re.search(
            r"^build-backend:.*?(?=^[a-zA-Z_-]+:|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "build-backend target не найден"
        body = match.group(0)

        # Убираем "uv pip download" из проверки (НЕ работает как команда)
        # Ищем реальные команды для скачивания wheels
        # Вариант 1: "uv run pip download ..." (правильно)
        # Вариант 2: "pip download ..." (если pip установлен)
        # НЕ ДОПУСКАЕТСЯ: "uv pip download ..." (НЕ существует в uv)
        assert "uv pip download" not in body, (
            "build-backend использует `uv pip download` — это НЕ существующий subcommand!\n"
            "Используйте `uv run pip download ...` или `pip download ...` через venv."
        )

        has_uv_run_pip = "uv run pip download" in body
        has_pip_download = bool(
            re.search(r"(?<![/a-z-])pip download", body)
        )
        assert has_uv_run_pip or has_pip_download, (
            "build-backend должен использовать `uv run pip download` или `pip download` "
            "для offline cache."
        )

    def test_build_backend_filters_editable(self, makefile_content: str) -> None:
        """build-backend должен отфильтровать editable (-e ./*) из requirements.txt.

        pip download не может обработать `-e ./*` пакеты (нет setup.py/wheel).
        Editable пакеты собираются из исходников в runtime stage.
        """
        match = re.search(
            r"^build-backend:.*?(?=^[a-zA-Z_-]+:|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert match
        body = match.group(0)
        # Должен быть grep -v '^-e' (или аналогичный фильтр)
        has_filter = (
            "grep -v '^-e" in body
            or "grep -E" in body
            or "requirements.deps.txt" in body
        )
        assert has_filter, (
            "build-backend должен отфильтровать editable пакеты (-e ./*) "
            "перед pip download"
        )


class TestMakefileDistributionTargets:
    """T-198b: export/import .tar для offline distribution (Яндекс.Диск)."""

    def test_export_images_target_exists(self, makefile_content: str) -> None:
        """make export-images создаёт .tar с всеми images."""
        assert re.search(r"^export-images:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `export-images:` для раздачи через Я.Диск"
        )

    def test_export_images_uses_docker_save(self, makefile_content: str) -> None:
        """export-images использует `docker save` для создания .tar."""
        match = re.search(
            r"^export-images:.*?(?=^[a-zA-Z_-]+:|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "export-images target не найден"
        body = match.group(0)
        assert "docker save" in body, (
            "export-images должен использовать `docker save`"
        )

    def test_import_images_target_exists(self, makefile_content: str) -> None:
        """make import-images TAR=path.tar загружает через docker load."""
        assert re.search(r"^import-images:", makefile_content, re.MULTILINE), (
            "Makefile должен иметь target `import-images:` для жюри"
        )

    def test_import_images_uses_docker_load(self, makefile_content: str) -> None:
        """import-images использует `docker load`."""
        match = re.search(
            r"^import-images:.*?(?=^[a-zA-Z_-]+:|\Z)",
            makefile_content,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "import-images target не найден"
        body = match.group(0)
        assert "docker load" in body, (
            "import-images должен использовать `docker load`"
        )
        assert "$(TAR)" in body, (
            "import-images должен принимать TAR=path.tar аргумент"
        )


class TestMakefileUpDependsOnBuild:
    """T-198b: make up должно автоматически генерировать wheels если их нет."""

    def test_up_depends_on_build_all(self, makefile_content: str) -> None:
        """up target должен иметь build-all как prerequisite."""
        # Ищем строку вида "up: build-all" или "up: ## ...\n\t$(MAKE) build-all"
        match = re.search(
            r"^up:\s*([^\n]*?)\s+##",
            makefile_content,
            re.MULTILINE,
        )
        if match:
            deps = match.group(1).strip()
            assert "build-all" in deps, (
                f"up target должен зависеть от build-all, got: {deps}"
            )
        else:
            # Альтернативный формат: up: target_deps
            up_line = re.search(r"^up:\s*(.+)$", makefile_content, re.MULTILINE)
            assert up_line, "up target не найден"
            assert "build-all" in up_line.group(1), (
                f"up должен зависеть от build-all, got: {up_line.group(1)}"
            )
