#!/bin/sh
# ============================================================================
# Transit-AI backend entrypoint (T-198e)
# ----------------------------------------------------------------------------
# Использует /usr/local/bin (system Python) — pip install в Dockerfile ставит
# туда. БЕЗ `uv sync` (он пытается resolve dev-deps: ipython).
# ============================================================================

set -eu

# T-198n: явный PYTHONPATH (USER 1000:1000 мог сбросить ENV PYTHONPATH)
export PYTHONPATH="/app/ml:/app"
export PATH="/usr/local/bin:/usr/bin:/bin"

if [ -z "${ALEMBIC_SYNC_DATABASE_URL:-}" ]; then
  ALEMBIC_SYNC_DATABASE_URL="${TRANSIT_AI_DATABASE_URL:-}"
  ALEMBIC_SYNC_DATABASE_URL="${ALEMBIC_SYNC_DATABASE_URL/asyncpg/psycopg2}"
  ALEMBIC_SYNC_DATABASE_URL="${ALEMBIC_SYNC_DATABASE_URL/aiosqlite/pysqlite}"
  export ALEMBIC_SYNC_DATABASE_URL
fi

export TRANSIT_AI_DATABASE_URL="${TRANSIT_AI_DATABASE_URL:-postgresql+asyncpg://transit:transit_dev_only@postgres:5432/transit_dev}"

echo "[entrypoint] DATABASE_URL = ${TRANSIT_AI_DATABASE_URL}"
echo "[entrypoint] ALEMBIC_SYNC = ${ALEMBIC_SYNC_DATABASE_URL}"
echo "[entrypoint] SEED_SKIP    = ${SEED_SKIP:-0}"

PYTHON_BIN="/usr/local/bin/python"
ALEMBIC_BIN="/usr/local/bin/alembic"

# Sanity check
if [ ! -f "$ALEMBIC_BIN" ]; then
  echo "[entrypoint] ERROR: $ALEMBIC_BIN not found (pip install failed?)"
  exit 1
fi

# 1. Alembic upgrade head — idempotent, создаёт таблицы если их нет
echo "[entrypoint] Running alembic upgrade head..."
cd /app/apps/backend
$ALEMBIC_BIN upgrade head || {
  echo "[entrypoint] ❌ alembic upgrade failed"
  exit 1
}

# 2. Seed predictions + actuals (idempotent — skip если таблицы не пустые)
if [ "${SEED_SKIP:-0}" = "1" ]; then
  echo "[entrypoint] SEED_SKIP=1 → skip seed"
else
  SEED_DATA_DIR="${SEED_DATA_DIR:-/app/data}"
  echo "[entrypoint] Running seed_predictions (data_dir=${SEED_DATA_DIR})..."
  TRANSIT_AI_DATABASE_URL="${TRANSIT_AI_DATABASE_URL}" \
    PYTHONPATH=/app \
    $PYTHON_BIN -m app.scripts.seed_predictions \
      --data-dir "${SEED_DATA_DIR}" || {
    echo "[entrypoint] ⚠️  seed_predictions failed (continuing — может данные уже есть)"
  }
fi

# 3. Запуск uvicorn (exec — PID 1 для корректного signal handling)
echo "[entrypoint] Starting uvicorn..."
cd /app
exec $PYTHON_BIN -m uvicorn app.main:app \
  --app-dir /app/apps/backend \
  --host 0.0.0.0 --port 8000 --workers 1 --log-level info
