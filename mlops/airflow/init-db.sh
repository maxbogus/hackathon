#!/usr/bin/env bash
# Transit-AI — инициализация метастора Airflow (T-235).
# ----------------------------------------------------------------------------
# 1) Создаёт БД `airflow` в общем Postgres, если её ещё нет (initdb-скрипты
#    postgres выполняются только при первой инициализации volume — он у нас уже есть).
# 2) Прогоняет `airflow db migrate`.
#
# Запускается сервисом airflow-init (см. docker-compose.yml, профиль `airflow`).
set -euo pipefail

: "${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:?AIRFLOW__DATABASE__SQL_ALCHEMY_CONN is required}"

echo "airflow-init: backend=${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN}"

python - <<'PY'
"""Создать БД для Airflow, если её нет (ждём доступности Postgres)."""
import os
import sys
import time

import psycopg2
from psycopg2 import sql

dsn = os.environ["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"].replace("+psycopg2", "")
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
                print(f"airflow-init: created database {db_name}", flush=True)
            else:
                print(f"airflow-init: database {db_name} already exists", flush=True)
        conn.close()
        sys.exit(0)
    except psycopg2.Error as exc:
        last_error = exc
        print(f"airflow-init: waiting for postgres ({attempt + 1}/30): {exc}", flush=True)
        time.sleep(2)

print(f"airflow-init: cannot reach postgres: {last_error}", file=sys.stderr, flush=True)
sys.exit(1)
PY

airflow db migrate

echo "airflow-init: done"
