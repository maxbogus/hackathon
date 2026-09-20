"""Health, version, readiness endpoints.

Routers mounted under /api/v1 — see app/main.py:create_app().
"""

from __future__ import annotations

import subprocess

from fastapi import APIRouter

from app import __version__
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["health"])


def _git_commit() -> str | None:
    """Best-effort git short SHA. None if not in a git repo."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            .decode()
            .strip()
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return None


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    """Returns 200 unconditionally — process is alive.

    No external dependencies are checked. Use `/readyz` for that.
    """
    return {"status": "ok"}


@router.get("/version", summary="Build info")
async def version() -> dict[str, str | None]:
    """Returns app version + git commit hash."""
    return {
        "version": __version__,
        "git_commit": _git_commit(),
        "app_env": settings.app_env,
    }


@router.get("/readyz", summary="Readiness probe")
async def readyz() -> dict[str, object]:
    """Returns 200 only if DB and Redis are reachable.

    Note: actual DB/Redis clients will be wired in T-016 (SQLAlchemy) and T-018
    (Redis client). For now, returns "ok" with a placeholder structure so the
    endpoint exists for k8s probes.
    """
    checks: dict[str, str] = {}

    # Placeholder: real DB check via get_db() in T-016
    # try:
    #     session: AsyncSession = next(get_db())
    #     await session.execute(text("SELECT 1"))
    #     checks["database"] = "ok"
    # except Exception as e:
    #     checks["database"] = f"error: {e}"

    # Placeholder: real Redis check in T-018
    # try:
    #     r = redis.Redis.from_url(settings.redis_url)
    #     await r.ping()
    #     checks["redis"] = "ok"
    # except Exception as e:
    #     checks["redis"] = f"error: {e}"

    checks["app"] = "ok"
    return {"status": "ok", "checks": checks}
