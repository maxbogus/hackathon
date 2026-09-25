# syntax=docker/dockerfile:1
# Transit-AI backend — FastAPI на uvicorn (T-164: hardened).
# R3 reproducible: pinned base image (python:3.12-slim-bookworm).
# Security: runs as non-root user (UID 1000).
# Build context: репо-корень (для uv workspace).

# ─── Stage 1: builder — deps через uv + создание non-root user ──────────────
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

# Install uv (один раз через pip — далее всё через uv)
RUN pip install --no-cache-dir uv==0.5.7

WORKDIR /app

# Копируем только манифесты для кэширования слоя deps
COPY pyproject.toml uv.lock* ./
COPY apps/backend/pyproject.toml ./apps/backend/

# Устанавливаем зависимости через uv (lockfile-aware, R3 reproducible)
RUN uv sync --frozen --no-dev --package transit-ai-backend 2>/dev/null || \
    uv sync --no-dev --package transit-ai-backend

# Создаём системного пользователя app (UID 1000, GID 1000)
RUN groupadd --system --gid 1000 app && \
    useradd --system --uid 1000 --gid app --shell /bin/bash --create-home app

# ─── Stage 2: runtime — только .venv + код, без pip/uv cache ───────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    WEB_CONCURRENCY=2

# uv нужен для CMD (один binary, ~30MB)
RUN pip install --no-cache-dir uv==0.5.7

# Создаём non-root пользователя app (UID 1000) в runtime stage
RUN groupadd --system --gid 1000 app && \
    useradd --system --uid 1000 --gid app --shell /bin/bash --create-home app

# Копируем .venv из builder (зависимости)
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Копируем исходники backend (с правильным ownership)
WORKDIR /app
COPY --from=builder --chown=app:app /app/apps/backend ./apps/backend

# Переключаемся на non-root пользователя ОБЯЗАТЕЛЬНО до CMD
USER app:app

# Volume для ML artefacts + data (read-only mount из docker-compose)
VOLUME ["/app/ml/artifacts", "/app/data"]

EXPOSE 8000

# Healthcheck (production-friendly: 30s интервал, 5s timeout, 3 retries, 15s start_period)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=15s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/healthz').raise_for_status()" || exit 1

# Запуск через uvicorn (2 workers для production)
CMD ["uv", "run", "--package", "transit-ai-backend", \
     "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--log-level", "info"]

