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
from app.api.alerts import router as alerts_router
from app.api.features import router as features_router
from app.api.health import router as health_router
from app.api.historical import router as historical_router
from app.api.models import router as models_router
from app.api.pipeline import router as pipeline_router
from app.api.predictions import router as predictions_router
from app.api.predictions_db import router as predictions_db_router
from app.api.load import router as load_router  # T-218: summary /load endpoints
from app.api.predictions_status import router as predictions_status_router
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
    app.include_router(predictions_router)
    app.include_router(predictions_db_router)  # T-195: from DB + export.csv
    app.include_router(load_router)  # T-218: /predictions/load, /historical/load
    app.include_router(historical_router)  # T-195: /historical/{route_id}
    app.include_router(models_router)
    app.include_router(alerts_router)
    app.include_router(features_router)  # T-195: /features, /zeros/toggle
    app.include_router(predictions_status_router)  # T-198: /predictions/status
    app.include_router(
        pipeline_router
    )  # T-198: /pipeline/full, /pipeline/status/{task_id}

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
