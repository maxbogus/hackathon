#!/bin/sh
# Transit-AI — entrypoint MLflow tracking server (T-235).
# ----------------------------------------------------------------------------
# 1) Создаёт БД `mlflow` в общем Postgres, если её ещё нет.
#    Почему не docker-entrypoint-initdb.d: скрипты postgres выполняются только
#    при первой инициализации volume, а он у нас уже существует (там transit_dev).
# 2) Запускает `mlflow server` с Postgres backend и локальным artifact store.
#
# Переменные:
#   MLFLOW_BACKEND_STORE_URI        postgresql+psycopg2://user:pass@host:5432/mlflow
#   MLFLOW_ARTIFACTS_DESTINATION    /mlartifacts (volume)
#
# F-137 (T-235): в MLflow 3.16 сервер в контейнере ронял uvicorn-воркеры на API-запросах
# (starlette WSGI responder: Empty reply from server / Connection reset), а его
# security-middleware требовал --allowed-hosts с портом и всё равно рвал соединения.
# Поэтому пинится Flask-based MLflow 2.16.2: security-middleware в нём нет, флаги
# 3.x (--allowed-hosts/--disable-security-middleware) не нужны. При переходе на 3.x
# вернуть их и явный список хостов + reverse proxy для общего слоя.

set -e

: "${MLFLOW_BACKEND_STORE_URI:?MLFLOW_BACKEND_STORE_URI is required}"
: "${MLFLOW_ARTIFACTS_DESTINATION:=/mlartifacts}"
# MLflow 3 проверяет Host-заголовок (DNS-rebinding защита) — сравнивает вместе с портом.
# Значение задаёт compose (MLFLOW_ALLOWED_HOSTS); дефолт — локальные варианты.
: "${MLFLOW_ALLOWED_HOSTS:=localhost,localhost:5001,127.0.0.1,127.0.0.1:5001,mlflow,mlflow:5000}"

echo "mlflow: backend=$MLFLOW_BACKEND_STORE_URI artifacts=$MLFLOW_ARTIFACTS_DESTINATION"

python - <<'PY'
"""Создать БД для MLflow, если её нет (ждём доступности Postgres)."""
import os
import sys
import time

import psycopg2
from psycopg2 import sql

dsn = os.environ["MLFLOW_BACKEND_STORE_URI"].replace("+psycopg2", "")
db_name = dsn.rsplit("/", 1)[-1]
admin_dsn = dsn.rsplit("/", 1)[0] + "/postgres"

last_error = None
for attempt in range(30):
    try:
        conn = psycopg2.connect(admin_dsn)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                print(f"mlflow: created database {db_name}", flush=True)
            else:
                print(f"mlflow: database {db_name} already exists", flush=True)
        conn.close()
        sys.exit(0)
    except psycopg2.Error as exc:
        last_error = exc
        print(f"mlflow: waiting for postgres ({attempt + 1}/30): {exc}", flush=True)
        time.sleep(2)

print(f"mlflow: cannot reach postgres: {last_error}", file=sys.stderr, flush=True)
sys.exit(1)
PY

exec mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --workers 4 \
    --backend-store-uri "$MLFLOW_BACKEND_STORE_URI" \
    --artifacts-destination "$MLFLOW_ARTIFACTS_DESTINATION" \
    --serve-artifacts
