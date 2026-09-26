# syntax=docker/dockerfile:1
# Transit-AI Sandbox (T-199) — restricted Python executor.
#
# Используется MCP tools (T-200) для безопасного выполнения кода,
# сгенерированного LLM. Изолирован через read-only root + no network + mem limit.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 1000 app && \
    useradd --system --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

COPY pyproject.toml ./
COPY app/ ./app/

# T-199: only stdlib (no uv needed). Install nothing extra.
USER app:app

# Sandbox workdir
RUN mkdir -p /tmp/sandbox && chown app:app /tmp/sandbox

# Hard limits via container runtime:
# --memory=256m --cpus=0.5 --network=none --read-only --tmpfs /tmp:size=50M

EXPOSE 8000

# MCP integration (T-200): import-only, no service
CMD ["python", "-c", "from app.executor import Sandbox; print('sandbox OK')"]
