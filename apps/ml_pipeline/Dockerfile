# syntax=docker/dockerfile:1
# Transit-AI ML Pipeline — Celery worker (T-193).
# R6 hackathon-rules: обучение ≤ 60 мин, поэтому увеличенный timeout.
# Build context: репо-корень (для uv workspace с ml/).

FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.5.7

WORKDIR /app

COPY pyproject.toml uv.lock* ./
COPY ml/pyproject.toml ./ml/
COPY apps/backend/pyproject.toml ./apps/backend/
COPY apps/ml_pipeline/pyproject.toml ./apps/ml_pipeline/

RUN uv sync --frozen --no-dev --package transit-ai-ml-pipeline 2>/dev/null \
 || uv sync --no-dev --package transit-ai-ml-pipeline

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
COPY --from=builder --chown=app:app /app/ml ./ml
COPY --from=builder --chown=app:app /app/apps/ml_pipeline ./apps/ml_pipeline

# ML artefacts + predictions mount (read-write)
VOLUME ["/app/ml/artifacts", "/app/predictions", "/app/data"]

USER app:app

CMD ["uv", "run", "--package", "transit-ai-ml-pipeline", \
     "celery", "-A", "app.celery_app:celery_app", \
     "worker", "--loglevel=info", "--concurrency=1"]
