"""Tests for T-198: docker-compose.yml поднимает полный стек.

RED phase: проверяем что make up поднимает ВСЕ сервисы (postgres + redis + backend + frontend + harvester + ml-pipeline).

После make up комиссия должна получить:
  - Frontend: http://localhost:5173 → 200 (AnalystDashboard работает)
  - Backend: http://localhost:8000 → 200 (через nginx проксирование)
  - Predictions: 14640 строк в БД (через entrypoint.sh seed)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE = REPO_ROOT / "docker-compose.yml"


@pytest.fixture()
def compose_content() -> str:
    assert COMPOSE.exists(), f"docker-compose.yml not found: {COMPOSE}"
    return COMPOSE.read_text()


class TestComposeStack:
    """docker-compose.yml поднимает полный стек для комиссии (T-198)."""

    def test_has_backend_service(self, compose_content: str) -> None:
        """Должен быть сервис `backend` в compose."""
        # Ищем строку вида "backend:" в секции services
        assert re.search(r"^  backend:", compose_content, re.MULTILINE), (
            "docker-compose.yml должен содержать сервис `backend:`"
        )

    def test_backend_depends_on_postgres_healthy(self, compose_content: str) -> None:
        """Backend должен ждать пока postgres станет healthy."""
        # Проверяем наличие depends_on с condition: service_healthy для postgres
        # в секции backend (грубый regex без YAML parser)
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section, "Backend service не найден"
        section = backend_section.group(0)
        assert "postgres" in section, "backend должен depends_on postgres"
        assert "service_healthy" in section, (
            "backend должен ждать service_healthy для postgres"
        )

    def test_backend_depends_on_redis(self, compose_content: str) -> None:
        """Backend должен depends_on redis (для cache + Celery result)."""
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section
        section = backend_section.group(0)
        assert "redis" in section, "backend должен depends_on redis"

    def test_backend_has_database_url_env(self, compose_content: str) -> None:
        """Backend должен иметь TRANSIT_AI_DATABASE_URL в env."""
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section
        section = backend_section.group(0)
        assert "TRANSIT_AI_DATABASE_URL" in section, (
            "backend должен иметь TRANSIT_AI_DATABASE_URL env var"
        )
        assert "postgres:5432" in section, (
            "TRANSIT_AI_DATABASE_URL должен указывать на postgres service"
        )

    def test_backend_has_seed_data_dir_env(self, compose_content: str) -> None:
        """Backend должен знать где лежит data/ для seed."""
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section
        section = backend_section.group(0)
        assert "SEED_DATA_DIR" in section, "backend должен иметь SEED_DATA_DIR env var"

    def test_backend_mounts_data_volume(self, compose_content: str) -> None:
        """Backend должен mount ./data:/app/data (для чтения CSV при seed)."""
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section
        section = backend_section.group(0)
        assert "/app/data" in section, "backend должен mount data в /app/data для seed"

    def test_backend_mounts_ml_and_predictions(self, compose_content: str) -> None:
        """Backend должен mount ml/ и predictions/ (для Celery tasks)."""
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section
        section = backend_section.group(0)
        assert "/app/ml" in section
        assert "/app/predictions" in section

    def test_backend_has_healthcheck(self, compose_content: str) -> None:
        """Backend должен иметь healthcheck на /api/v1/healthz."""
        backend_section = re.search(
            r"^  backend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert backend_section
        section = backend_section.group(0)
        assert "healthcheck:" in section, "backend должен иметь healthcheck"
        assert "healthz" in section, "backend healthcheck должен проверять /healthz"


class TestPipelineWorkers:
    """Harvester + ml-pipeline должны подниматься по умолчанию (без --profile)."""

    def test_harvester_no_profile(self, compose_content: str) -> None:
        """Harvester НЕ должен быть под профилем (должен стартовать по умолчанию)."""
        # Грубый regex: между "harvester:" и следующим сервисом не должно быть profiles:
        harvester_section = re.search(
            r"^  harvester:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert harvester_section, "harvester service не найден"
        section = harvester_section.group(0)
        # profiles: ["pipeline"] или profiles: [pipeline] — НЕ должно быть
        assert not re.search(r"profiles:\s*\[", section), (
            "harvester НЕ должен быть под profiles: (должен стартовать по умолчанию)"
        )

    def test_ml_pipeline_no_profile(self, compose_content: str) -> None:
        """ml-pipeline НЕ должен быть под профилем."""
        ml_section = re.search(
            r"^  ml-pipeline:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert ml_section, "ml-pipeline service не найден"
        section = ml_section.group(0)
        assert not re.search(r"profiles:\s*\[", section), (
            "ml-pipeline НЕ должен быть под profiles: (должен стартовать по умолчанию)"
        )


class TestFrontendNginx:
    """Frontend nginx должен проксировать на backend в compose-сети."""

    def test_frontend_no_extra_hosts(self, compose_content: str) -> None:
        """Frontend НЕ должен иметь extra_hosts: host.docker.internal.

        Backend теперь в compose → nginx должен ходить на `backend:8000`,
        а не на host.docker.internal.
        """
        frontend_section = re.search(
            r"^  frontend:.*?(?=^  [a-z]|^volumes:|^networks:)",
            compose_content,
            re.MULTILINE | re.DOTALL,
        )
        assert frontend_section
        section = frontend_section.group(0)
        assert "extra_hosts" not in section, (
            "frontend НЕ должен иметь extra_hosts (backend теперь в compose)"
        )
        assert "host.docker.internal" not in section, (
            "frontend НЕ должен ссылаться на host.docker.internal"
        )
