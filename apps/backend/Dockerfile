# syntax=docker/dockerfile:1
# Transit-AI backend — offline build через pre-built wheels (T-198b, T-198h).
# R3 reproducible: pinned base + uv export lockfile.
#
# T-198h: БЕЗ passwd пакета (apt-get install фейлит в закрытой сети).
#         Создаём пользователя app вручную через /etc/passwd + /etc/group.

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/usr/local/bin:/usr/bin:/bin"

WORKDIR /app

# T-236: uv в runtime-образе НЕ нужен — зависимости ставятся из pre-built wheels
# через pip (--no-index --find-links), а CMD/entrypoint используют системный python.
# Раньше здесь был `pip install uv==0.5.7` — единственный сетевой шаг сборки,
# из-за которого offline-build ломался без интернета.

# T-198h: non-root user через /etc/passwd (без useradd/groupadd).
# UID 1000, GID 1000 для совместимости с volumes на хосте.
RUN echo 'app:x:1000:1000:app user:/app:/bin/sh' >> /etc/passwd \
 && echo 'app:x:1000:' >> /etc/group \
 && mkdir -p /app /home/app \
 && chown -R 1000:1000 /app /home/app

# Pre-built wheels
COPY --chown=1000:1000 apps/backend/requirements.txt /tmp/

# T-198c: фильтруем editable
RUN grep -v '^-e \.' /tmp/requirements.txt > /tmp/requirements.deps.txt \
 && rm /tmp/requirements.txt

COPY --chown=1000:1000 apps/backend/wheels /tmp/wheels

# T-198e: pip install в system Python
RUN pip install --no-index --find-links=/tmp/wheels/ -r /tmp/requirements.deps.txt \
 && rm -rf /tmp/wheels /tmp/requirements.deps.txt

# Workspace sources (owned by user 1000)
COPY --chown=1000:1000 pyproject.toml uv.lock* README.md ./
# F-096: docs/schemas/prediction_artifact.schema.json нужен ArtifactLoader в runtime
# (REPO_ROOT/docs/schemas/prediction_artifact.schema.json = /app/docs/...)
COPY --chown=1000:1000 docs /app/docs
COPY --chown=1000:1000 ml/pyproject.toml ml/README.md ./ml/
# T-198m: копируем исходный код transit_ai (workspace package)
COPY --chown=1000:1000 ml/transit_ai /app/ml/transit_ai
COPY --chown=1000:1000 ml/configs /app/ml/configs
COPY --chown=1000:1000 ml/scripts /app/ml/scripts
COPY --chown=1000:1000 apps/backend/pyproject.toml ./apps/backend/
COPY --chown=1000:1000 apps/backend/app /app/apps/backend/app
COPY --chown=1000:1000 apps/backend/scripts /app/apps/backend/scripts

COPY --chown=1000:1000 apps/backend/alembic.ini /app/apps/backend/alembic.ini
COPY --chown=1000:1000 apps/backend/alembic /app/apps/backend/alembic

# T-198l: PYTHONPATH=/app/ml для transit_ai.* import
ENV PYTHONPATH=/app/ml
# Switch to non-root user
USER 1000:1000

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=90s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/healthz').raise_for_status()" || exit 1

CMD ["/app/apps/backend/scripts/entrypoint.sh"]
