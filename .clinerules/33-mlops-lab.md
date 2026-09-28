# 33-mlops-lab.md — MLOps лаборатория (`mlops/`): изоляция, тесты, сервисы

## Зачем

`mlops/` — side-car лаборатория (MLflow, DVC, Optuna, Airflow) рядом с P0-пайплайном.
Она должна оставаться **изолированной и удаляемой** (`rm -rf mlops/` не ломает продукт),
при этом её тесты не должны отравлять основной гейт, а сервисы — конфликтовать с портами
соседних проектов. Правила зафиксированы после пилота T-235.

## R1. Изоляция от P0

- ❌ MLflow / DVC / Optuna / Airflow **не** добавляются в `uv.lock`, `pyproject.toml` ядра,
  `apps/*` — ставятся эфемерно (`uv run --with …`) либо живут в отдельном образе.
- ✅ Инструменты лаборатории можно удалить вместе с каталогом: код продукта от них не зависит.
- ✅ Артефакты лаборатории gitignored: `mlops/airflow_home/`, `mlops/airflow/logs/`,
  `mlops/optuna/studies/`, `mlops/dvc-cache/`, `mlruns.db`, `mlartifacts/`.

## R2. Тесты лаборатории живут только в `mlops/tests/`

- ❌ Не класть в `ml/tests/`: там тесты продукта, и они должны быть герметичными и быстрыми.
  Лабораторные тесты требуют эфемерных пакетов/сети → раньше валили `make test` (F-125).
- ✅ Обязателен `pytest.importorskip(...)` для эфемерной зависимости.
- ✅ Пути считать от репозитория (`Path(__file__).resolve().parents[2]`), не хардкодить.
- Команды: `make mlops-test` (герметичный контур), `make mlops-test-full` (эфемерные
  optuna/dvc/apache-airflow), точечно — `make optuna-test|dvc-test|airflow-test`.

## R3. DAG-инвариант (переносимость в общий Airflow)

- ❌ DAG не импортирует код проекта (`app.*`, `transit_ai.*`) и не вызывает `subprocess`/`uv`.
- ✅ Все стадии — Celery-задачи **по имени** через `mlops/dags/_celery_client.py`
  (`send`/`wait`, allowlist `TASKS`).
- ✅ Это проверяется AST-тестом: `mlops/tests/test_airflow_dag_structure.py`
  (`test_dag_does_not_import_project_code`, `test_tasks_use_celery_client_not_subprocess`).
- Зачем: перенос DAG-а в общий оркестратор = смена bundle, а не правка кода; и внутри
  контейнера Airflow нет ни репозитория, ни uv-окружения (F-133).

## R4. Очереди Celery разделены по воркерам

- ✅ `ml_pipeline.*` → очередь `ml_pipeline`, `harvester.*` → `harvester`
  (`task_default_queue` в `apps/*/app/celery_app.py`, `queue_for()` в клиенте).
- ❌ Не отправлять задачи в default-очередь: два воркера слушают её одновременно и задача
  может достаться чужому → `NotRegistered` (F-141).

## R5. Сервисы лаборатории — профили compose, порты только через env

- Профили: `mlops` (MLflow), `airflow` (Airflow: init/dag-processor/scheduler/api-server),
  `pipeline` (Celery-воркеры), `loadtest` (k6).
- ✅ Публикуется минимум портов, все — через `${*_HOST_PORT}`; занятые порты хоста:
  5000 (`registry:2`), 8080/8081 (ai-gateway) → MLflow 5001, Airflow 8087.
- ✅ Метаданные MLflow/Airflow живут в БД существующего postgres (`mlflow`, `airflow`),
  создаются entrypoint-ом сервиса (initdb-скрипты на готовом volume не срабатывают).
- ✅ Версии инструментов пинуются в их Dockerfile (R3): `mlflow==2.16.2` + `sqlalchemy<2.1`,
  `apache-airflow:3.3.2-python3.12` + `celery[redis]`.

## R6. Тяжёлые тесты продукта — вне быстрого гейта

- ✅ Тесты, обучающие модель на полном датасете организаторов, помечаются
  `pytestmark = pytest.mark.slow`; `make test` идёт с `-m "not slow"`, отдельный прогон —
  `make test-slow` (F-136).
- Тесты, требующие данных вне git, скипаются через `ml/tests/_data_guards.py`
  (`requires_spravochnik`), а не падают (F-127).

## R7. Проверка результата — числами, а не глазами

- Сверка submission-ов: `uv run python scripts/compare_submissions.py --left A --right B`
  (структура 10×61×24, нули, сумма, число различающихся ключей, max|Δ|).
- Отчёт пилота: `docs/reports/repro_best_vs_pilot.md` — критерий Tier A (детерминизм +
  структура + числовая сверка с объяснением расхождения).

## Cross-references

- `mlops/MLOPS_LAB.md` — отчёт лаборатории (что дало результат, что нет)
- `docs/MLFLOW.md` — трекер и сервис
- D-044 (создание лаборатории), D-047 (изоляция тестов, Airflow в Docker, DAG-инвариант),
  D-048 (раннер ML в воркере), D-049 (критерий Tier A)
- F-125, F-127, F-132, F-133, F-136, F-137, F-138, F-140, F-141
