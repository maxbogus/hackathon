# MLOPS_LAB.md — сравнение 4 инструментов числами

> Дата: 2026-09-27
> Этапы: 0-6 завершены в коммитах `8024e1d` → `3f63542`.
> Цель: изолированная side-car MLOps лаборатория в `mlops/` рядом с P0-пайплайном,
> без правок `apps/*`, `uv.lock`, `pyproject.toml`, `docker-compose.yml`.

## Резюме одним абзацем

Все 4 инструмента (MLflow, DVC, Optuna, Airflow) установлены **эфемерно** через
`uv run --with …` (не в `uv.lock`), работают рядом с P0-пайплайном и заменяют
5 разрозненных форматов хранения метаданных (CSV/JSON/MD/ledger/DB) одним
`search_runs` / `git status` / `optuna.study.trials`. Side-car pipeline
`lineage → ingest → leaderboard` оркестрируется через Airflow DAG
(`transit_pipeline`) с manual trigger. DVC даёт 0 GB overhead на 9.7 GB
датасетах через hardlink (ext4). Optuna TPE находит surrogate-best 0.83
за 1.9 сек (15 trials). Идемпотентность ingest обеспечивается через
`transit_ai.ingest_key` тег в MLflow (повторный прогон — no-op, 0.2 сек).

## Таблица сравнения

| Инструмент | Версия | Размер env | Время install | Что заменили | Метрика "полезность" |
|---|---|---|---|---|---|
| **MLflow** | 3.16.1 | 88 пакетов | 3.2 сек | 5 форматов (CSV/JSON/MD/ledger/DB) → 1 `search_runs` | 81 source за 3.6 сек; повтор — 0.2 сек (idempotent) |
| **DVC** | 3.67.1 | 62 пакета | 0.1 сек (cached) | manual provenance файлов | 9.7 GB / 0 GB overhead (hardlink ext4, inode=34222104, link count=2) |
| **Optuna** | 5.0.0 | 12 пакетов | 8 ms (cached) | ручной grid sweep | 15 trials / 1.9 сек, TPE нашёл best=0.8306 рядом с target=0.875 |
| **Airflow** | 3.3.2 | 132 пакета | 29 ms (cached) | bash-скрипты для pipeline | DAG с 3 тасками, sequential chain через `>>`, `tasks test` smoke = exit 0 |

## Что было ДО и стало ПОСЛЕ

| Было | Стало | Этап |
|---|---|---|
| `train_data_hash: "pending"` в meta.json | sha256 из `docs/lineage/datasets/real_ridership.json` (312 байт JSON) | 2 |
| 23 артефакта + 53 манифеста + 5 отчётов в 3 разных местах | 81 MLflow run с тегами source/ingest_key, `search_runs` API | 3 |
| grep по `docs/ledger/findings.jsonl` для ответа "что залито на платформу" | `make mlflow-leaderboard` → таблица 53 сабмитов с drift | 3 |
| `train.csv` 8 GB без provenance для offline-сдачи жюри | DVC-указатель `train.csv.dvc` (95 байт), `dvc pull` восстанавливает | 4 |
| ручной sweep `xgboost_sweep` (~5-7 точек) | Optuna TPE 15 trials, sqlite storage, resumable | 5 |
| bash-скрипт для "fetch → ingest → leaderboard" | Airflow DAG `transit_pipeline` с 5 тасками и зависимостями (T-235) | 6 |

## Реальные цифры (с машин, не из плана)

### MLflow (3.16.1)
```
$ make mlflow-test           → 16/16 тестов зелёные за 2.8 сек
$ make mlflow-demo           → 3 рана + nested folds, run_name = xgboost_demo-0/1, gru_demo-2
$ make mlflow-ingest         → created=81 skipped=0 errors=0 time=3.6 sec
$ make mlflow-ingest  (повтор)→ created=0  skipped=81 errors=0 time=0.2 sec   ← идемпотентность
$ make mlflow-leaderboard    → 53 submissions, 3/53 submitted, avg drift = -0.5561
```

### DVC (3.67.1) на ext4
```
$ dvc add data/real/train.csv  (8 GB)  → 18.0 sec, cache 9.75 GB, free НЕ изменился
inode train.csv = 34222104, inode cache = 34222104, link count = 2  ← настоящий hardlink
$ dvc add data/real/test.csv  (2.1 GB)  → 6.0 sec
$ dvc add 23× ml/artifacts/*/model.pkl  → 25 sec суммарно
$ dvc status                          → "Data and pipelines are up to date"
$ du -sh mlops/dvc-cache              → 9.8G (показывает размер, но disk не растёт благодаря hardlink)
```

### Optuna (5.0.0) TPE + sqlite
```
$ make optuna-smoke  (2 trials)  → best=0.6213, ~2 sec, детерминирован (seed=42)
$ uv run --with optuna python -c "...create_study(n_trials=15)..."
  → 15 trials, best=0.8306, best_params: n_estimators=278, max_depth=8, lr=0.054
  → рядом с target (n_est=300, depth=6, lr=0.05)
storage: mlops/optuna/studies/xgboost_route.db (sqlite, resumable)
```

### Airflow (3.3.2) DAG
```
$ uv run --with apache-airflow python -c "import airflow; print(airflow.__version__)"
  → 3.3.2 за 3 сек
$ make airflow-test         → 7/7 тестов (DAG imports, 5 tasks, sequential deps)
$ airflow tasks test transit_pipeline harvest 2026-01-01  → exit 0
$ airflow dags list | grep transit
  → transit_pipeline | mlops_dags bundle | schedule=None
```

> **T-235 (2026-09-28):** side-car DAG `transit_side_car` (lineage → ingest →
> leaderboard через `uv subprocess`) **удалён**. Причина: внутри контейнера
> Airflow uv-окружения нет — `uv run` создаёт `.venv` и тянет ML-стек из сети
> (F-133). Единственный DAG — `transit_pipeline` (5 стадий), все шаги ставятся
> Celery-задачами **по имени** через `mlops/dags/_celery_client.py`, то есть
> оркестратор не импортирует код проекта и переносится в общий Airflow без правок.

## Что ДАЛО реальный результат

1. **MLflow leaderboard** (`make mlflow-leaderboard`) — самая практичная вещь:
   одной командой видим все 53 submission-а с drift local↔platform. До этого
   приходилось grep-ать `docs/ledger/findings.jsonl` вручную.
2. **DVC hardlink на ext4** — ровно 0 GB overhead на 9.7 GB. Жюри может
   `git clone` + `make dvc-init` + `dvc pull` без скачивания 10 GB (только
   `.dvc` указатели).
3. **Lineage snapshot** (`make lineage-snapshot-real`) — 312-байтный JSON
   коммитится в git как provenance для 8 GB файла. Заменяет `hash_dataframe`
   который pickle-ит в RAM и OOM-ит.
4. **Airflow DAG** (`transit_pipeline`) — даже без scheduler, ручной
   `airflow tasks test` доказывает что pipeline reproducible.

## Что НЕ ДАЛО результата / overhead

1. **Airflow env** (132 пакета, ~3 сек install) — для 3-таскового DAG
   это **overkill**. Простой bash-скрипт сделал бы то же за 0.1 сек.
   Оправдание: DAG даёт retries/backfill/UI из коробки, которых у bash нет.
2. **Optuna на surrogate** — surrogate-best 0.83 vs реальный best 0.8751
   из ручного sweep (xgboost_sweep). TPE не побил ручной результат, но
   автоматизация экономит время на новых гиперпараметрах.

## Граничные условия (когда НЕ работает)

| Инструмент | Граничное условие | Поведение |
|---|---|---|
| DVC hardlink | FS ≠ ext4/xfs/btrfs (например tmpfs, NFS без поддержки) | fallback на `copy` (+9.7 GB) |
| MLflow file-store | MLflow 3.x — в maintenance mode | исключение без `MLFLOW_ALLOW_FILE_STORE=true`; дефолт переключён на SQLite (F-112) |
| Airflow LocalExecutor | один процесс без параллелизма | для демо OK, для production → celery/k8s executor |
| Optuna sqlite storage | concurrent writes | нужен PostgreSQL/MySQL backend для multi-process |

## Roadmap для production

| Приоритет | Что | Зачем | Effort |
|---|---|---|---|
| P1 | `mlflow server` в Docker с persistent volume | central tracking server для команды | 4 ч |
| P1 | `airflow scheduler` + `webserver` в `docker-compose.yml` (отдельный профиль `airflow`) | DAG trigger по расписанию, UI на :8080 | 6 ч |
| P2 | Real XGBoost objective в Optuna (`build_real_objective(df_subset)`) | production-grade HPO вместо surrogate | 4 ч |
| P2 | `predictions.csv.dvc` для всех submissions | provenance для каждого submission файла | 2 ч |
| P3 | DVC remote (S3/MinIO) вместо local | бэкап + multi-machine | 3 ч |

## Контракты (не сломали)

- ✅ `apps/*` не тронуты (0 файлов modified)
- ✅ `uv.lock` не тронут (все 4 инструмента эфемерные)
- ✅ `pyproject.toml` не тронут (нет новых runtime-зависимостей)
- ✅ `docker-compose.yml` не тронут (Airflow — отдельный профиль `mlops/`)
- ✅ `make check-all` остаётся зелёным
- ✅ Conventional Commits по этапам (см. git log)

## Где смотреть

| Что | Путь |
|---|---|
| MLflow store | `mlruns.db` (sqlite, gitignored) |
| MLflow runs | `make mlflow-leaderboard` / `make mlflow-ui` → :5000 |
| Lineage snapshots | `docs/lineage/datasets/*.json` (10 файлов, в git) |
| DVC config | `.dvc/config` (no_scm, hardlink cache) |
| DVC cache | `mlops/dvc-cache/files/md5/...` (gitignored, hardlink в ext4) |
| Optuna study | `mlops/optuna/studies/xgboost_route.db` (sqlite, gitignored) |
| Airflow DAG | `mlops/dags/transit_pipeline.py` (+ `_celery_client.py`) |
| Airflow home | `mlops/airflow_home/` (airflow.cfg + airflow.db, gitignored) |
| Ledger | `docs/ledger/{decisions,findings}.jsonl` (+ F-112..F-118) |

## Команды Makefile

```bash
make mlflow-probe          # MLflow версия
make mlflow-demo           # 3 рана + nested folds
make mlflow-test           # 16 тестов трекера
make mlflow-ingest         # идемпотентный ingest 81 source
make mlflow-leaderboard    # drift-таблица local vs platform
make mlflow-ui             # MLflow UI :5000

make lineage-snapshot-real # 8 GB train.csv → 312-байт JSON
make lineage-test          # 14 тестов lineage-пакета
make lineage-verify        # sha256 в meta.json == snapshot

make dvc-probe             # DVC версия + filesystem support
make dvc-init              # init + hardlink cache config
make dvc-status            # "Data and pipelines are up to date"
make dvc-cache-size        # du -sh mlops/dvc-cache
make dvc-test              # 2 теста probe

make optuna-probe          # Optuna версия
make optuna-smoke          # 2-trial smoke (~2 sec)
make optuna-run            # 15-trial TPE (~30 sec на real XGBoost)
make optuna-test           # 6 тестов storage/deтерминизм

make airflow-probe         # Airflow version + db migrate
make airflow-dags-list     # список DAGs
make airflow-tasks-list    # tasks в transit_pipeline
make airflow-test-task TASK=harvest  # одна таска без scheduler
make airflow-test          # тесты структуры DAG (AST-контур + импорт в Airflow)
make airflow-trigger       # ручной запуск DAG через scheduler
```
