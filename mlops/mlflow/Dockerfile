# syntax=docker/dockerfile:1
# Transit-AI — MLflow tracking server (T-235, профиль `mlops`).
# ----------------------------------------------------------------------------
# Side-car инфраструктура: MLflow НЕ попадает в uv.lock/apps/* (clinerule 10,
# D-044). Backend store — БД `mlflow` в существующем Postgres, артефакты —
# локальный volume /mlartifacts (host: ./mlartifacts).
#
# pip используется один раз — для установки uv (как в остальных Dockerfile проекта),
# дальше пакеты ставит uv в системный python.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Версия MLflow запинована (R3 reproducible): 2.16.2 — Flask-based сервер.
# Почему не 3.16.x: сервер MLflow 3 в контейнере роняет uvicorn-воркеры на API-запросах
# (starlette WSGI responder, DeprecationWarning → Empty reply from server/Connection reset),
# из-за чего клиенты не могут работать. F-137.
RUN pip install --no-cache-dir uv==0.5.7 \
 && uv pip install --system \
      "mlflow==2.16.2" \
      "sqlalchemy<2.1" \
      "gunicorn>=22.0" \
      "psycopg2-binary>=2.9" \
 && rm -rf /root/.cache/uv

COPY mlops/mlflow/entrypoint.sh /usr/local/bin/mlflow-entrypoint
RUN chmod +x /usr/local/bin/mlflow-entrypoint

EXPOSE 5000

# F-137 (T-235): HEALTHCHECK намеренно отсутствует. Проверка через
# `python -c urllib.request.urlopen(...)` внутри контейнера роняла MLflow
# (процесс завершался с кодом 0 → docker restart loop). Доступность проверяем
# снаружи: `curl http://localhost:${MLFLOW_HOST_PORT}/health`.

ENTRYPOINT ["/usr/local/bin/mlflow-entrypoint"]
