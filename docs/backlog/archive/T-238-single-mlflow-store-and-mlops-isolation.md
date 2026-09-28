---
id: T-238
phase: 7
title: Single MLflow store and honest mlops isolation invariant
priority: P2
effort: 2
unit: hours
rice:
  R: 3
  I: 2
  C: 0.9
  score: 2.7
depends_on: [T-236, T-237]
blocks: []
tags: [mlops, delivery, docs]
status: done
created: 2026-09-28
updated: 2026-09-28
assignee: ""
---

## Context

Заключительные два противоречия, которые комиссия прочитала бы как вопрос к нам
(продолжение T-236/T-237):

1. **Два store у MLflow без указания канона.** Локальный sqlite (`mlruns.db`) и сервер
   на Postgres (профиль `mlops`, :5001) сосуществовали, а `docs/MLFLOW.md` не говорил,
   какой из них канон. Документы могли ссылаться на раны, которых у получателя нет (D-052).
2. **Инвариант изоляции не совпадал с фактом.** D-044 и `mlops/README.md` обещали
   «`rm -rf mlops/` не ломает пайплайн», но `Makefile` импортировал `mlops.*` в 6 местах
   (`optuna-smoke/run`, `pipeline-train/predict/full/script`), а сам DAG-bundle живёт в
   `mlops/dags/` (F-150).

## Acceptance Criteria

- [x] `docs/MLFLOW.md`: канон для отчётов и сдачи — сервер (`make mlflow-up`, :5001, Postgres);
      локальный sqlite — `[dev]`-режим, не источник цифр (D-052)
- [x] Цели `mlflow-ui|mlflow-server|mlflow-demo|mlflow-runs|mlflow-run` помечены `[dev]` в `make help`
- [x] `Makefile` не импортирует `mlops.*`: `pipeline-*` отправляют задачи в продуктовый
      воркер (`docker compose exec` + `send_task` + `r.get()`), `optuna-*` / `airflow-*` /
      `mlflow-up` защищены `mlops-lab-guard`
- [x] Инвариант в `.clinerules/33-mlops-lab.md`, `mlops/README.md`, `docs/MLFLOW.md`
      переформулирован честно: продукт и приёмка не зависят от `mlops/`, lab-возможности опциональны
- [x] `_celery_client` остался в bundle (перенос в `apps/*` нарушил бы DAG-инвариант)

## Technical Notes

- Guard печатает, что именно теряется без `mlops/`, и что при этом продолжает работать
  (`make up` / `make export-verify` / `make check-all`).
- `pipeline-predict` принимает `MODEL_ID=...` (по умолчанию `xgboost_v_default`).
- Канон оркестрации — DAG (`make airflow-trigger`); `pipeline-*` — dev-путь без Airflow.

## Verification

```bash
grep -c 'from mlops' Makefile          # 0
make mlflow-up                         # guard → сервер :5001
make pipeline-script SCRIPT=lineage_snapshot   # SUCCESS (send_task + r.get)
make mlops-test                        # 18 passed / 2 skipped
make export-verify                     # OK (14 файлов, 62 хэша)
```

## Status

`done` (2026-09-28). Результаты:

| Проверка | Результат |
|---|---|
| `grep -c 'from mlops' Makefile` | 0 (было 6) |
| `make mlflow-up` | guard пройден, сервер `http://localhost:5001` поднят |
| `make pipeline-script SCRIPT=lineage_snapshot` | `SUCCESS`, sha256 `e4157ed7…`, 25.1 с |
| `make mlops-test` | 18 passed / 2 skipped |
| `make export-verify` | OK: 14 обязательных файлов, 62 хэша |

Находка и решение: F-150 (импорты `mlops.*` в Makefile), D-052 (единый store MLflow),
D-053 (честный инвариант изоляции).
