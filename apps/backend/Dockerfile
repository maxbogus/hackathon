# syntax=docker/dockerfile:1
# Transit-AI backend — FastAPI на uvicorn.
# Build context: репо-корень (для uv workspace).

# ─── Stage 1: deps + app ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

# Install uv
RUN pip install --no-cache-dir uv==0.5.7

WORKDIR /app

# Копируем только манифесты для кэширования слоя
COPY pyproject.toml uv.lock* ./
COPY apps/backend/pyproject.toml ./apps/backend/

# Устанавливаем зависимости через uv (быстрее pip, lockfile-aware)
RUN uv sync --frozen --no-dev --package transit-ai-backend 2>/dev/null || \
    uv sync --no-dev --package transit-ai-backend

# Копируем исходники
COPY apps/backend ./apps/backend

# Volume для ML artefacts + data (read-only mount из docker-compose)
VOLUME ["/app/ml/artifacts", "/app/data"]

EXPOSE 8000

# Healthcheck (используется в docker-compose)
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/healthz').raise_for_status()" || exit 1

# Запуск через uvicorn (entrypoint из main:app появится в T-014)
CMD ["uv", "run", "--package", "transit-ai-backend", \
     "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
