# syntax=docker/dockerfile:1
# Transit-AI — Airflow 3.3.2 (профиль `airflow`, T-235).
# ----------------------------------------------------------------------------
# Оркестратор только ставит Celery-задачи по имени (mlops/dags/_celery_client.py),
# поэтому в образе НЕТ ML-зависимостей (ни torch, ни xgboost, ни uv-окружения) —
# только celery+redis как клиент брокера. DAG-и монтируются из ./mlops/dags.
#
# Изоляция (D-044): Airflow не попадает в uv.lock/pyproject.toml; версия пинуется
# здесь (R3). Метастор — БД `airflow` в существующем postgres.

FROM apache/airflow:3.3.2-python3.12

# Официальный образ запрещает pip от root ("Please use 'airflow' user to run pip!") —
# ставим celery от пользователя airflow и копируем init-скрипт под root.
USER root
COPY mlops/airflow/init-db.sh /usr/local/bin/airflow-init-db
RUN chmod +x /usr/local/bin/airflow-init-db

USER airflow
# celery[redis] — клиент для send_task/AsyncResult в DAG-тасках.
RUN pip install --no-cache-dir "celery[redis]>=5.4.0,<6"

# DAG bundle: ./mlops/dags монтируется в /opt/airflow/dags (docker-compose.yml)
EXPOSE 8080
