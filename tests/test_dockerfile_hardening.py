"""Tests for apps/backend/Dockerfile hardening (T-164).

Validates security/reproducibility requirements from clinerule 01-safety.md:
non-root user, pinned base image, sane healthcheck parameters.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "apps" / "backend" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dockerfile_text() -> str:
    assert DOCKERFILE.exists(), f"Missing {DOCKERFILE}"
    return _read(DOCKERFILE)


# === Multi-stage build ===


def test_dockerfile_uses_multi_stage() -> None:
    """Multi-stage build обязателен для R3 reproducible (тикет T-164)."""
    text = _dockerfile_text()
    from_count = text.count("FROM ")
    assert from_count >= 2, f"Dockerfile must use multi-stage build (≥2 FROM). Got: {from_count}"


def test_dockerfile_has_builder_stage() -> None:
    """Multi-stage должен включать builder stage для deps."""
    text = _dockerfile_text()
    assert re.search(r"FROM\s+\S+\s+AS\s+builder", text, re.IGNORECASE), (
        "Dockerfile must have explicit 'AS builder' stage"
    )


def test_dockerfile_runtime_copies_from_builder() -> None:
    """Runtime stage должен копировать .venv из builder, не ставить deps повторно."""
    text = _dockerfile_text()
    assert re.search(r"COPY\s+--from=builder", text, re.IGNORECASE), (
        "Runtime stage must use 'COPY --from=builder' to inherit .venv"
    )


# === Security: non-root user ===


def test_dockerfile_creates_app_user() -> None:
    """Должен создаваться системный user app с UID 1000."""
    text = _dockerfile_text()
    # useradd в builder (до runtime)
    assert "useradd" in text or "adduser" in text, (
        "Dockerfile must create non-root user via useradd/adduser"
    )
    assert re.search(r"uid\s*=?\s*1000|--uid\s+1000|-u\s+1000", text), (
        "User must be created with UID 1000"
    )


def test_dockerfile_uses_non_root() -> None:
    """USER app (или UID 1000) обязателен перед CMD/ENTRYPOINT."""
    text = _dockerfile_text()
    # Должно быть USER app или USER 1000
    assert re.search(r"USER\s+(app|1000)(?::\w+)?\s*$", text, re.MULTILINE), (
        "Dockerfile must set USER app (or USER 1000) before CMD"
    )


def test_user_directive_before_cmd() -> None:
    """USER должен быть объявлен ДО CMD (иначе эффекта нет)."""
    text = _dockerfile_text()
    user_match = re.search(r"^USER\s+", text, re.MULTILINE)
    cmd_match = re.search(r"^CMD\s+", text, re.MULTILINE)
    assert user_match and cmd_match, "USER and CMD directives required"
    assert user_match.start() < cmd_match.start(), (
        f"USER must precede CMD. USER@{user_match.start()} vs CMD@{cmd_match.start()}"
    )


# === Reproducibility: pinned base image ===


def test_dockerfile_no_latest_tag() -> None:
    """Base image НЕ должен использовать :latest (R3 reproducible)."""
    text = _dockerfile_text()
    # FROM python:3.12-slim-bookworm — OK. FROM python:latest — нет.
    bad = re.findall(r"FROM\s+\S+:latest\b", text)
    assert not bad, f"Base image must not use :latest. Got: {bad}"


def test_dockerfile_pins_bookworm_or_slim() -> None:
    """Base image должен быть pinned: python:3.12-slim-bookworm (или digest)."""
    text = _dockerfile_text()
    # Сейчас допустим python:3.12-slim-bookworm (тикет явно требует это)
    assert re.search(r"FROM\s+python:3\.12-slim-bookworm", text), (
        "Base image must be pinned: python:3.12-slim-bookworm"
    )


# === Healthcheck ===


def test_dockerfile_healthcheck_interval_ge_30s() -> None:
    """HEALTHCHECK --interval=30s или больше (production-friendly)."""
    text = _dockerfile_text()
    # Найти --interval=<N>s или --interval=<N>m
    m = re.search(r"--interval=(\d+)([sm])", text)
    assert m, "HEALTHCHECK must specify --interval"
    value = int(m.group(1))
    unit = m.group(2)
    seconds = value if unit == "s" else value * 60
    assert seconds >= 30, f"HEALTHCHECK interval must be ≥30s for production. Got: {value}{unit}"


def test_dockerfile_healthcheck_retries_ge_3() -> None:
    """HEALTHCHECK --retries ≥ 3 (clinerule 01-safety)."""
    text = _dockerfile_text()
    m = re.search(r"--retries=(\d+)", text)
    assert m, "HEALTHCHECK must specify --retries"
    assert int(m.group(1)) >= 3, f"HEALTHCHECK retries must be ≥3. Got: {m.group(1)}"


def test_dockerfile_healthcheck_has_start_period() -> None:
    """HEALTHCHECK должен иметь --start-period для cold start."""
    text = _dockerfile_text()
    assert "--start-period" in text, "HEALTHCHECK should specify --start-period for app warm-up"


# === .dockerignore ===


def test_dockerignore_exists() -> None:
    """.dockerignore обязателен для ускорения build + исключения секретов."""
    assert DOCKERIGNORE.exists(), f"Missing {DOCKERIGNORE}"


@pytest.mark.parametrize(
    "pattern",
    [".venv", "__pycache__", ".git", ".env", "node_modules", ".pytest_cache"],
)
def test_dockerignore_excludes(pattern: str) -> None:
    """.dockerignore должен исключать .venv, кэши, секреты."""
    text = _read(DOCKERIGNORE)
    assert pattern in text, f".dockerignore must exclude {pattern}"


# === EXPOSE / CMD ===


def test_dockerfile_exposes_8000() -> None:
    """EXPOSE 8000 сохранён (FastAPI default)."""
    text = _dockerfile_text()
    assert re.search(r"^EXPOSE\s+8000\b", text, re.MULTILINE), "Dockerfile must EXPOSE 8000"


def test_dockerfile_cmd_uses_uvicorn() -> None:
    """CMD должен запускать uvicorn через uv."""
    text = _dockerfile_text()
    assert "uvicorn" in text, "CMD must run uvicorn"
    assert "uv" in text, "CMD should use uv runner"
