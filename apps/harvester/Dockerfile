# syntax=docker/dockerfile:1
# Transit-AI Harvester — Celery worker (T-193).
# R3 reproducible: pinned base + uv 0.5.7.
# Build context: репо-корень (для uv workspace).

# ─── Stage 1: builder — deps через uv ─────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.5.7

WORKDIR /app

# Копируем манифесты для deps-слоя
COPY pyproject.toml uv.lock* ./
COPY apps/harvester/pyproject.toml ./apps/harvester/

# --frozen даёт reproducible (R3); fallback без lockfile для dev
RUN uv sync --frozen --no-dev --package transit-ai-harvester 2>/dev/null \
 || uv sync --no-dev --package transit-ai-harvester

# ─── Stage 2: runtime ──────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.5.7
RUN groupadd --system --gid 1000 app && \
    useradd --system --uid 1000 --gid app --shell /bin/bash --create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
WORKDIR /app
COPY --from=builder --chown=app:app /app/apps/harvester ./apps/harvester

# data dir mount
VOLUME ["/app/data/external"]

USER app:app

# Default: celery worker (override в docker-compose)
CMD ["uv", "run", "--package", "transit-ai-harvester", \
     "celery", "-A", "app.celery_app:celery_app", \
     "worker", "--loglevel=info", "--concurrency=2"]
