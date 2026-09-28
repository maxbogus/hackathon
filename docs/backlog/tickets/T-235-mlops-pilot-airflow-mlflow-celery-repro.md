---
id: T-235
phase: 3
title: MLOps pilot — Airflow+MLflow над Celery, воспроизводимость best submission
priority: P1
effort: 13
unit: hours
rice:
  R: 4
  I: 2
  C: 0.8
  score: 0.492
depends_on: []
blocks: []
tags: [mlops, airflow, mlflow, celery, reproducibility, infra]
status: in-progress
created: 2026-09-28
updated: 2026-09-28
assignee: ""
---

# T-235: MLOps pilot — Airflow+MLflow над Celery, воспроизводимость best submission

## Context

После хакатона осталась MLOps-лаборатория (`mlops/`, D-044), но она не доведена
до рабочего контура: Airflow = DAG без оркестратора (schedule=None, нет
scheduler/api-server, нет сервиса в compose), MLflow = локальный sqlite (не сервер),
а **лучший сабмит (0.83455, F-083) не воспроизводим**: его базовая модель
`xgboost_v11_base_only` утрачена, манифест ссылается на несуществующий
`route_baseline_v1`, `dataset_hash_sha256: "unknown"`, а постобработка
(holiday/cold-snap множители) живёт в библиотеке `schedule_overrides.py`, которую
**никто из пайплайна не вызывает** — она применялась ad-hoc скриптом (F-127).

Пилот (Tier A) отвечает на вопрос «сможем ли повторить решение за час»:
тонкий Airflow-оркестратор над существующими Celery-воркерами + MLflow-сервер +
промоушен рецепта best-сабмита в CLI. Глобализация (общие пакеты, общий DAG,
ручки оркестрации с локальным запуском) — отдельный этап после проверки пилота.

## Acceptance Criteria

- [x] Фаза 0: `make test` зелёный (mlops-тесты вынесены в `mlops/tests/`, `importorskip`), `make mlops-test` зелёный
- [ ] Фаза 1: `--overrides-file` в `make_submission.py` (порядок: `pred_cap` → `zero_route` → overrides), `ml/configs/overrides/nov_dec_2025.yaml` (профили A/B), unit-тесты
- [x] Фаза 2: `mlops/dags/_celery_client.py` (send/wait по имени, ноль импортов `app.*`); Celery-таск `ml_pipeline.run_ml_script` (allowlist lineage/mlflow_ingest/mlflow_leaderboard); `make pipeline-*` переведены на клиент
- [ ] Фаза 3: MLflow-сервер в профиле `mlops` (Postgres-БД `mlflow`), `track_run` с тегами `airflow_dag_run_id`/`submission_id`
- [ ] Фаза 4: DAG `transit_pipeline` (harvest→train→ingest→predict→leaderboard, retries/timeout/params) + Airflow-профиль в Docker (init/scheduler/api-server, `AIRFLOW_HOST_PORT`, метастор БД `airflow`)
- [ ] Фаза 5: отчёт `docs/reports/repro_best_vs_pilot.md` + ledger + clinerule 33 + HANDOFF

## Technical Notes

- **Инвариант**: DAG не импортирует код проекта (`app.*`, `transit_ai.*`) — только
  `send_task` по имени через bare Celery-клиент. Проверяется AST-тестом
  (`mlops/tests/test_airflow_dag_structure.py::test_dag_does_not_import_project_code`).
  Это делает перенос в общий Airflow бесплатным (меняется bundle, не DAG).
- **Порядок постобработки** (из манифеста эталона A):
  `clip_negatives → per_route_log_bias_calibration → pred_cap_55(h0-4) → zero_route_5 →
  holiday_override(03.11×0.5, 04.11×0.5, 31.12×0.7) → cold_snap(23–31.12×0.92)`.
- **Критерий «такой же результат» (Tier A)**: детерминизм (2 прогона побитово равны)
  + структура (14640 строк = 10 маршрутов × 61 день × 24 ч) + числовая сверка с
  эталонами `predictions/submission_route_baseline_v1_*_20260926T1711{06,40}Z.csv`
  (нули / сумма / расхождения) с объяснением дрейфа.
- **MLflow — сервер, а не sqlite**: параллельные писатели (Airflow-таск + Celery-воркеры)
  ловят SQLite-локи; сервер = один писатель, и он же локальная копия глобального
  (переезд = смена `MLFLOW_TRACKING_URI`).
- **Порты**: 5000 занят `registry:2`, 8080/8081 — ai-gateway → Airflow `8087`, MLflow `5001`.

## Verification

```bash
# Фаза 0 (готово)
make test                 # 725 passed, 22 skipped (ml 419 + backend 284 + assistant 13 + mcp 9)
make mlops-test           # 8 passed, 2 skipped (герметично, < 1 c)
make airflow-test         # 7 passed (AST-контур + импорт DAG в Airflow 3.3.2)

# Фаза 1+
make submission ARGS="--overrides-file ml/configs/overrides/nov_dec_2025.yaml --overrides-profile a_conservative"
make mlflow-up && make pipeline-up && make airflow-up
make airflow-trigger DAG=transit_pipeline
make mlflow-leaderboard
```

## Status

`in-progress` — Фаза 0 (изоляция mlops-тестов, зелёный `make test`) и Фаза 1
(`--overrides-file` + YAML-профили) закрыты; Фаза 2 проверена end-to-end:
`send('run_ml_script', script='lineage_snapshot')` → воркер → системный python →
sha256 `train.csv` совпал с эталоном (25.9 s).

**Блокеры, найденные по ходу (ledger):**
- F-127 — справочник организаторов (xlsx) отсутствует → xgboost-путь (train/predict)
  невыполним; baseline-путь работает.
- F-132 — pre-built wheels и `requirements.txt` уехали в `docs/apps/**` → образ
  воркера нельзя пересобрать (обход: `make pipeline-worker-dev`).
- F-133 — в образе нет `pyyaml` (+ нет uv-окружения) → ML-шаги в Docker не работали;
  исправлено объявлением зависимости и настраиваемым раннером (`ML_PIPELINE_ML_RUNNER`).
