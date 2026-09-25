"""Verify docker-compose has resource limits for all services (T-163).

R3 hackathon-rules: reproducible environment with explicit resource limits.
k6 loadtest profile must use CPU pinning to isolate load from backend.

Note: docker compose v2 uses top-level keys (mem_limit, cpus, pids_limit)
rather than deploy.resources (which is swarm-only).
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def load_compose() -> dict:
    """Load docker-compose.yml as YAML."""
    assert COMPOSE_FILE.exists(), f"docker-compose.yml not found at {COMPOSE_FILE}"
    with COMPOSE_FILE.open() as f:
        return yaml.safe_load(f)


def test_compose_file_is_yaml() -> None:
    """docker-compose.yml должен валидно парситься как YAML."""
    compose = load_compose()
    assert "services" in compose, "docker-compose.yml missing 'services' key"


def test_all_services_have_mem_limit() -> None:
    """Каждый сервис должен иметь mem_limit (top-level, не deploy.resources)."""
    compose = load_compose()
    services = compose["services"]
    main_services = [name for name in services if name != "k6"]
    assert len(main_services) >= 4, (
        f"Expected at least 4 main services, got {len(main_services)}: {list(services.keys())}"
    )
    for name in main_services:
        cfg = services[name]
        mem = cfg.get("mem_limit")
        assert mem is not None, f"Service {name!r} missing mem_limit"


def test_all_services_have_cpus_limit() -> None:
    """Каждый сервис должен иметь cpus (top-level)."""
    compose = load_compose()
    services = compose["services"]
    for name in services:
        if name == "k6":
            continue
        cfg = services[name]
        cpus = cfg.get("cpus")
        assert cpus is not None, f"Service {name!r} missing cpus limit"


def test_backend_has_pids_limit() -> None:
    """Backend должен иметь pids_limit для защиты от fork-бомб."""
    compose = load_compose()
    backend = compose["services"].get("backend")
    assert backend is not None, "backend service missing"
    pids = backend.get("pids_limit")
    assert pids is not None, "backend missing pids_limit (fork-bomb protection)"


def test_k6_service_exists() -> None:
    """Профиль loadtest должен содержать сервис k6."""
    compose = load_compose()
    k6 = compose["services"].get("k6")
    assert k6 is not None, "k6 service missing from docker-compose.yml"


def test_k6_in_loadtest_profile() -> None:
    """k6 должен быть в профиле loadtest (не запускается по умолчанию)."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    profiles = k6.get("profiles", [])
    assert "loadtest" in profiles, (
        f"k6 must be in 'loadtest' profile. Got profiles: {profiles}"
    )


def test_k6_has_cpu_pinning() -> None:
    """k6 должен иметь CPU pinning (cpuset) для изоляции нагрузки от backend."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    cpuset = k6.get("cpuset")
    assert cpuset is not None, (
        "k6 missing cpuset (CPU pinning). Required for load isolation from backend."
    )
    assert isinstance(cpuset, str) and len(cpuset) > 0, (
        f"k6 cpuset must be non-empty string. Got: {cpuset!r}"
    )


def test_k6_uses_grafana_image() -> None:
    """k6 должен использовать официальный образ grafana/k6 с pinned версией."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    image = k6.get("image", "")
    assert image.startswith("grafana/k6:"), (
        f"k6 must use grafana/k6 image. Got: {image!r}"
    )
    assert not image.endswith(":latest"), (
        f"k6 image must be pinned, not :latest. Got: {image!r}"
    )


def test_k6_mounts_tests_load() -> None:
    """k6 должен монтировать ./tests/load как /scripts."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    volumes = k6.get("volumes", [])
    has_tests_load = any(
        "./tests/load" in str(v) and "/scripts" in str(v) for v in volumes
    )
    assert has_tests_load, (
        f"k6 must mount ./tests/load as /scripts. Got volumes: {volumes}"
    )


def test_k6_mounts_reports_dir() -> None:
    """k6 должен монтировать ./docs/load-profiles/reports для HTML-отчётов."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    volumes = k6.get("volumes", [])
    has_reports = any(
        "load-profiles/reports" in str(v) for v in volumes
    )
    assert has_reports, (
        f"k6 must mount reports dir. Got volumes: {volumes}"
    )


def test_k6_has_web_dashboard_env() -> None:
    """k6 должен иметь K6_WEB_DASHBOARD=true для графиков."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    env = k6.get("environment", {})
    assert env.get("K6_WEB_DASHBOARD") == "true", (
        f"k6 must have K6_WEB_DASHBOARD=true. Got: {env}"
    )
    assert env.get("K6_WEB_DASHBOARD_PORT") == "5665", (
        f"k6 must have K6_WEB_DASHBOARD_PORT=5665. Got: {env}"
    )


def test_k6_uses_host_network() -> None:
    """k6 должен использовать network_mode: host для прямого доступа к backend."""
    compose = load_compose()
    k6 = compose["services"]["k6"]
    net_mode = k6.get("network_mode")
    assert net_mode == "host", (
        f"k6 must use network_mode: host. Got: {net_mode!r}"
    )
