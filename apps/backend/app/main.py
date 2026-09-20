"""FastAPI application factory.

Запуск:
    uv run uvicorn app.main:app --reload --port 8000

Routes:
    GET  /api/v1/healthz    — liveness probe (no deps)
    GET  /api/v1/version    — version + git commit
    GET  /api/v1/readyz     — readiness probe (checks DB + Redis)
    GET  /openapi.json      — generated OpenAPI schema
    GET  /docs              — Swagger UI
"""

from __future__ import annotations

import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.config import settings


def _git_commit() -> str | None:
    """Best-effort git short SHA. Returns None if not in a git repo."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode().strip()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks. Reserved for future DB/Redis pool init."""
    yield


def create_app() -> FastAPI:
    """Application factory. Used by uvicorn and by tests."""
    app = FastAPI(
        title="Transit-AI Backend",
        version=__version__,
        description="Прогноз пассажиропотока трамваев Москвы (hackathon Transit-AI).",
        lifespan=lifespan,
    )

    # CORS — frontend dev servers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {
            "app": "transit-ai-backend",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    return app


app = create_app()


__all__ = ["_git_commit", "app", "create_app"]
