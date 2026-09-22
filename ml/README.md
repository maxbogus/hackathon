# Transit-AI — ML Pipeline

ML-пайплайн прогноза пассажиропотока трамваев Москвы (хакатон Transit-AI).
**Обучение и inference выполняются скриптами (вне Docker)** — см.
`.clinerules/10-ml-as-scripts.md`. Артефакты моделей пишутся на диск в
`ml/artifacts/<model_id>/`, backend читает их через `apps/backend/forecast/loader.py`.

## Установка

```bash
# Из корня репо
uv sync --extra dev
```

## Основные команды

| Команда | Что делает |
|---|---|
| `make seed` | Сгенерировать синтетические данные → `data/synthetic/` |
| `make train-baseline` | BaselineMean (mean by hour/day/route) |
| `make train-xgboost` | XGBoost predictor (T-028) |
| `make train-gru` | GRU с attention pooling (T-029) |
| `make train-hybrid` | Hybrid (GRU + LGBM blend, T-030) |
| `make predict` | Сгенерировать прогнозы → `predictions/*.parquet` (T-033) |
| `make calibrate` | Применить per-bucket калибровку (T-034) |
| `make evaluate` | Метрики RMSLE/MAE/MAPE (T-035) |
| `make benchmark-baseline` | Smoke benchmark (~30 сек) |
| `make benchmark-all` | Полный grid по всем моделям |

## Структура

```
ml/
├── transit_ai/
│   ├── data/             # DataSource ABC, Synthetic, Real (адаптер под parquet/csv)
│   ├── models/           # BaselineMean, XGBoost, GRU, Hybrid
│   ├── training/         # train.py, predict.py, calibrate.py, evaluate.py, registry.py
│   ├── benchmark/        # benchmark pipeline (T-038)
│   ├── montecarlo/       # scenario simulator (T-036)
│   └── reports/          # метрики и графики
├── scripts/              # entry-points (вызываются из Makefile)
├── configs/              # YAML гиперпараметры + per-machine overrides
├── artifacts/            # .gitignore: обученные модели
└── tests/                # unit + integration
```

## Контракт артефакта

Каждая обученная модель лежит в `ml/artifacts/<model_id>/`:

```
ml/artifacts/baseline_v1/
├── meta.json          # model_id, kind, version, trained_at, git_commit, metrics
├── model.pkl          # сериализованная модель (pickle/joblib)
├── preprocessor.pkl   # scaler, encoder
└── calibration.json   # per-bucket biases (после T-034)
```

`meta.json` валидируется через JSON Schema (`docs/schemas/prediction_artifact.schema.json`)
при загрузке в backend. Если артефакт невалиден — API вернёт 503 с понятной ошибкой.

## Reproducibility (R3 hackathon-rules)

- Random seed фиксирован в каждом скрипте через `--seed` (default 42)
- `git_commit` записывается в `meta.json` (анти-фрод)
- `train_data_hash` (sha256 от parquet) пишется в `meta.json`
- Все версии зафиксированы в `uv.lock` (коммитится)
