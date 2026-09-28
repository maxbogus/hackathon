# MLFLOW.md — MLflow в Transit-AI (observability-слой, НЕ источник истины)

> Реализация: `ml/transit_ai/tracking/` (`mlflow_tracker.py`, `__init__.py`).
> Отчёт лаборатории: `mlops/MLOPS_LAB.md`. Решение: D-044. Находки: F-112, F-113, F-115.

## Зачем

MLflow заменяет 5 разрозненных форматов метаданных (`CSV`/`JSON`/`MD`/`ledger`/`DB`)
одним API `search_runs`. Это **наблюдаемость**, а не контракт: если MLflow убрать,
пайплайн обязан работать как раньше (см. «Мягкая деградация»).

## Источники истины (MLflow их НЕ заменяет)

| Что | Где живёт |
|---|---|
| Артефакт модели (контракт) | `ml/artifacts/<model_id>/meta.json` + `model.pkl` (JSON Schema — `docs/schemas/prediction_artifact.schema.json`) |
| Сабмит (контракт) | `predictions/submission_<model>_<start>_<end>_<run_ts>.{csv,json}` (clinerule 23) |
| Реестр активной модели | `ml/artifacts/active.json` |
| Продовые прогнозы | Postgres `predictions` (`is_active` / `is_etalon`) |
| Решения/находки | `docs/ledger/{decisions,findings}.jsonl` |

MLflow — вторичный слой: его можно пересоздать из перечисленного (`make mlflow-ingest`).

## Мягкая деградация

`track_run()` становится no-op, если:
- `mlflow` не импортируется (его нет в `uv.lock` — ставится эфемерно), **или**
- `TRANSIT_AI_MLFLOW` ∈ `{0,false,no,off}`.

ML-скрипты при этом работают как обычно и **ничего не пишут на диск**.

## Переменные окружения

| Переменная | Default | Смысл |
|---|---|---|
| `TRANSIT_AI_MLFLOW` | включено, если `mlflow` импортируется | глобальный выключатель трекера |
| `MLFLOW_TRACKING_URI` | `sqlite:///<repo>/mlruns.db` | backend store |
| `TRANSIT_AI_MLFLOW_ARTIFACTS` | `file:<repo>/mlartifacts` | artifact root |
| `TRANSIT_AI_MLFLOW_EXPERIMENT` | `transit-ai` | имя эксперимента (fallback: `MLFLOW_EXPERIMENT_NAME`) |
| `MLFLOW_ALLOW_FILE_STORE` | — | включается автоматически, если выбран `file:`-store |

> Почему по умолчанию SQLite, а не file-store: в MLflow 3 файловый backend переведён
> в maintenance mode и по умолчанию **кидает исключение** (F-112). Переключение на
> сервер (`http://mlflow:5000`) — это только смена `MLFLOW_TRACKING_URI`, код не меняется.

## Команды

```bash
make mlflow-probe        # версия MLflow (эфемерная установка, uv.lock не трогаем)
make mlflow-demo         # 3 конфига × 4 fold → nested runs в mlruns.db
make mlflow-runs         # список ранов из локального store (LIMIT=N)
make mlflow-ui           # UI → http://127.0.0.1:$(MLFLOW_PORT) (sqlite)
make mlflow-server       # локальный tracking server (sqlite) для клиентов
make mlflow-ingest       # идемпотентный ingest 81 источника
make mlflow-ingest-only KIND=artifacts|manifests|benchmarks
make mlflow-leaderboard  # drift-таблица: local holdout vs platform (top-30)
make mlflow-test         # 16 тестов трекера (ml/tests/test_mlflow_tracker.py)
make mlflow-run SCRIPT=scripts/train_xgboost.py ARGS="--model-id x"   # любой скрипт под tracking
```

## Идемпотентный ingest

`make mlflow-ingest` обходит три типа источников (`ml/transit_ai/lineage/ingest.py`):

- `ArtifactSource` — `ml/artifacts/*/meta.json` + `model.pkl`
- `ManifestSource` — `predictions/*.json` (манифесты сабмитов)
- `BenchmarkSource` — `docs/reports/benchmark_*.csv`

Ключ идемпотентности — `sha256` самого файла, тег рана `transit_ai.ingest_key`.
Повторный прогон даёт `created=0 skipped=N` (проверено: 81 источник за 3.6 с, повтор 0.2 с).
**Порядок важен:** ingest нужно запускать сразу после обучения — иначе удалённый (или
перезаписанный) артефакт уже не попадёт в store (см. F-127 в ledger).

## Drift-таблица (`make mlflow-leaderboard`)

Читает раны `transit_ai.source = 'submission-manifest'` и строит таблицу
`submission_id | holdout_wape_score | platform_score | drift` с сортировкой по holdout.
Заменяет ручной grep по `docs/ledger/findings.jsonl`.
Метрики: `WAPE-score ∈ [0,1]`, больше = лучше (clinerule 27).

## MLflow как сервис (профиль `mlops`, T-235)

**Канон для передачи (T-238, D-052):** все раны, на которые ссылаются отчёты и сдача,
живут в **сервере** — `make mlflow-up` (профиль `mlops`, Postgres-БД `mlflow`, порт
`${MLFLOW_HOST_PORT:-5001}`), клиенты ходят через
`export MLFLOW_TRACKING_URI=http://localhost:5001`.

Локальный sqlite (`mlruns.db`) — **`[dev]`-режим** для одиночных прогонов на одной машине:
он не поставляется, не переносится и не должен быть источником цифр в документах
(цели `mlflow-ui`, `mlflow-server`, `mlflow-demo`, `mlflow-runs`, `mlflow-run`).
Для оркестрации (DAG + Celery-воркеры + несколько клиентов) обязателен сервер — один
писатель вместо конкурирующих процессов за SQLite.

```bash
make mlflow-up      # profile: mlops -> http://localhost:5001 (+ создаст БД mlflow в postgres)
make mlflow-url     # печатает export MLFLOW_TRACKING_URI=http://localhost:5001
make mlflow-logs    # хвост логов сервера
make mlflow-down    # остановить

# клиенты:
export MLFLOW_TRACKING_URI=http://localhost:5001
make mlflow-ingest          # 81 источник (идемпотентно)
make mlflow-leaderboard     # drift-таблица против сервера
```

| Параметр | Значение |
|---|---|
| Образ | `mlops/mlflow/Dockerfile` — `mlflow==2.16.2` + `sqlalchemy<2.1` + `gunicorn` + `psycopg2-binary` |
| Backend store | БД `mlflow` в существующем `postgres` (entrypoint создаёт её при старте) |
| Артефакты | volume `./mlartifacts` (host) ↔ `/mlartifacts` (контейнер), `--serve-artifacts` |
| Порт | `${MLFLOW_HOST_PORT:-5001}` (5000 занят локальным `registry:2`) |
| Версия клиента | `MLFLOW_PKG ?= mlflow==2.16.2` (совпадает с сервером), переопределяется: `MLFLOW_PKG="mlflow>=2.16" make ...` |

**Грабли (F-137), если будете менять версию/конфиг:**
- sqlalchemy резолвится как 2.1 → MLflow падает `ImportError: cannot import name 'FallbackAsyncAdaptedQueuePool'` → пиньте `sqlalchemy<2.1`.
- MLflow 3.x-сервер в контейнере ронял uvicorn-воркеры на API-запросах (`Empty reply from server`), а его security-middleware требовал `--allowed-hosts` вместе с портом — поэтому пинится 2.16.2.
- `HEALTHCHECK` через `python -c urllib…` внутри контейнера роняет сервер → healthcheck отключён, проверяйте снаружи: `curl localhost:5001/health`.
- Смена мажорной версии MLflow на существующей БД → `alembic Can't locate revision`; пересоздайте БД: `DROP DATABASE mlflow;` (работы перезаливаются `make mlflow-ingest`).

## Изоляция (не ломать)


- ❌ MLflow **не** добавляется в `uv.lock` / `pyproject.toml` / `docker-compose.yml`
  (кроме сервиса в профиле `mlops`/`airflow` — см. `mlops/README.md`).
- ❌ Никто не читает MLflow в runtime (`apps/*`): только ML-скрипты и `make mlflow-*`.
- ❌ Артефакты-контракты не «переезжают» в MLflow: источник истины — файлы/БД.
- ✅ `mlops/` можно удалить (`rm -rf mlops/`) — пайплайн не сломается; lab-цели
  (`airflow-*`, `mlflow-up`, `optuna-*`) требуют каталог и падают с понятным
  сообщением (`make mlops-lab-guard`, T-238).

## Тесты

Режим no-op (без mlflow) и режим tracking проверяются в
`ml/tests/test_mlflow_tracker.py` (`make mlflow-test`). Тесты лаборатории
(optuna/airflow) живут отдельно — `mlops/tests/` (`make mlops-test`).

## См. также

- `mlops/MLOPS_LAB.md` — сравнение 4 инструментов числами
- `docs/lineage/datasets/*.json` — lineage-снимки (sha256 датасетов)
- `.clinerules/33-mlops-lab.md` — правила изоляции лаборатории
