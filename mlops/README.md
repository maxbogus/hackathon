# mlops/ — MLOps side-car lab

Изолированная лаборатория для 4 инструментов (MLflow, DVC, Optuna, Airflow).
Все 4 устанавливаются **эфемерно** через `uv run --with …`, не попадают в `uv.lock`,
не требуют правок `apps/*`, `pyproject.toml`, `docker-compose.yml`.

## Структура

```
mlops/
├── MLOPS_LAB.md           # сравнение 4 инструментов числами (отчёт)
├── README.md              # этот файл (how-to-use)
├── dags/
│   ├── transit_pipeline.py # Airflow DAG: harvest → train → ingest → predict → leaderboard
│   └── _celery_client.py   # тонкий клиент: задачи по имени (без импорта кода воркеров)
├── optuna/
│   ├── study_xgboost.py   # Optuna TPE study для XGBoost route-only
│   └── studies/           # sqlite storage (gitignored)
├── airflow_home/          # AIRFLOW_HOME (gitignored): airflow.db + cfg
├── dvc-cache/             # DVC hardlink cache (gitignored)
├── tests/                 # тесты лаборатории (изолированы от ml/tests, см. clinerule 33)
└── probes/
    └── dvc_probe.sh       # probe-скрипт для DVC версии + FS support
```

## Что даёт каждый инструмент

| Инструмент | Главная команда | Метрика |
|---|---|---|
| MLflow | `make mlflow-leaderboard` | drift local↔platform по 53 сабмитам |
| DVC | `dvc pull` (на новой машине) | 9.7 GB датасеты без скачивания (через `.dvc` указатели) |
| Optuna | `make optuna-run` | 15 trials TPE за ~30 сек |
| Airflow | `airflow tasks test transit_pipeline harvest 2026-01-01` | одна таска без scheduler |

Подробности — в `MLOPS_LAB.md`.

## Как добавить новый pipeline

1. **MLflow tracker** — в любом ML-скрипте: `from transit_ai.tracking import track_run`
2. **Lineage snapshot** — для нового датасета: `make lineage-snapshot INPUT=path OUTPUT=path`
3. **DVC tracking** — `uv run --with dvc dvc add <file>`
4. **Optuna study** — копируй `mlops/optuna/study_xgboost.py`, меняй objective
5. **Airflow DAG** — добавь новый файл в `mlops/dags/`, допиши таски

## Изоляция от P0

- ✅ `apps/*` — 0 модификаций
- ✅ `uv.lock` — 0 модификаций
- ✅ `pyproject.toml` — 0 модификаций (нет новых runtime-зависимостей)
- ✅ `docker-compose.yml` — 0 модификаций
- ✅ `make check-all` — зелёный

Все 4 инструмента можно удалить за `rm -rf mlops/` без последствий для P0.
