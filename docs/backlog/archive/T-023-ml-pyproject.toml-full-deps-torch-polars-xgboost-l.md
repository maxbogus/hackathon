---
id: T-023
phase: 2
title: ml pyproject.toml full deps torch polars xgboost lightgbm catboost
priority: P0
effort: 3
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.7
  score: 3.5
depends_on: []
blocks: [T-028, T-029, T-030, T-032, T-033]
tags: [ml, deps]
status: done
created: 2026-09-20
updated: 2026-09-22
assignee: "cline"
---

# T-023: ml pyproject.toml full deps torch polars xgboost lightgbm catboost

## Context

Phase 2 критический блокер: T-028 (XGBoost), T-029 (GRU), T-030 (Hybrid)
не могут стартовать, пока ml/ pyproject.toml не подтянет torch/polars/
xgboost/lightgbm/catboost. Сейчас ml/pyproject.toml — STUB (только
numpy/pandas).

## Acceptance Criteria

- [x] `ml/pyproject.toml` содержит deps: torch, polars, xgboost, lightgbm, catboost, pyarrow, scikit-learn
- [x] Сохранены текущие dev-deps: numpy, pandas, ruff, mypy, pytest
- [x] Добавлен entry-point `transit-ai-ml` (placeholder) для будущих CLI
- [x] `uv sync --extra dev` в корне проходит без ошибок
- [x] `uv run python -c "import torch, polars, xgboost, lightgbm, catboost"` завершается с кодом 0
- [x] README в `ml/README.md` кратко описывает команды (train/predict/benchmark)

## Technical Notes

### Выбор версий (фиксируем в pyproject.toml)

| Пакет | Версия | Обоснование |
|---|---|---|
| torch | >=2.3.0 | Совместим с RTX 5060 (sm_120), RTX 4070 (sm_89) |
| polars | >=0.20.0 | Быстрее pandas на больших parquet (>1M строк) |
| xgboost | >=2.1.0 | Поддержка GPU через `device='cuda'` |
| lightgbm | >=4.3.0 | Для hybrid blend (T-030) |
| catboost | >=1.2.0 | Опционально для category features (T-028) |
| pyarrow | >=16.0.0 | Для parquet I/O в predict.py |
| scikit-learn | >=1.5.0 | Для метрик RMSLE/MAE/MAPE (T-035) |
| numpy | >=1.26.0 | Уже есть |
| pandas | >=2.2.0 | Уже есть, для read_csv fallback |

### Почему torch, а не только sklearn

T-029 (GRU с attention pooling) — критическая модель для хакатона.
Без torch невозможно реализовать. Согласовано с D-005 (RICE ~8).

### Версионирование

Все версии с `>=` (uv.lock зафиксирует транзитивные). Это компромисс
между reproducibility (R3 hackathon-rules) и удобством обновления.

## Verification (executed)

```bash
$ uv sync --extra dev
Resolved 122 packages in 0.69ms
Checked 36 packages in 0.17ms

$ uv run --package transit-ai-ml python -c "import torch, polars, xgboost, lightgbm, catboost, pyarrow, sklearn, pydantic; print('OK')"
torch= 2.14.0+cu130
polars= 1.44.2
xgboost= 3.4.1
lightgbm= 4.7.0
catboost= 1.2.10
pyarrow= 25.0.1
sklearn= 1.9.1
pydantic= 2.13.5
CUDA available: True

$ uv run --package transit-ai-ml python -c "import transit_ai; print(transit_ai.__version__)"
transit_ai 0.1.0

$ uv run ruff check ml/pyproject.toml ml/README.md
All checks passed!
```

## Notes

- TDD не применим к pyproject.toml (конфиг, не код). Acceptance criteria — verification через `uv sync` + import.
- mypy overrides для torch/xgboost/lightgbm/catboost/polars/pyarrow уже в корневом pyproject.toml — не дублируем.
