# 10-ml-as-scripts.md — Почему ML не в Docker

## Решение

ML обучается **скриптами** в `ml/` через `make train-*`. Не через Docker.

## Почему

### 1. GPU доступ
Docker требует `--gpus all` или `nvidia-container-runtime`.
Часто это сломано на Mac, Linux без правильной установки драйверов, в WSL.
Скрипты — просто `uv run python script.py`. GPU через `torch.cuda.is_available()`.

### 2. Артефакты на диске
Модели — это файлы (model.pkl, model.pt, model.onnx).
Версионируются через `meta.json` (model_id, git_commit, train_data_hash, seed, metrics).
Переключение активной модели = atomic rename в `ml/artifacts/active/`.

### 3. Переиспользование кода
Скрипты легко копировать между проектами.
Docker-образы — большие, долго собирать, привязаны к ОС.

### 4. Быстрый цикл разработки
- Меняешь фичу → `uv run python train.py` → 30 секунд
- В Docker: rebuild image → 5 минут

### 5. Разделение concerns
- Backend: HTTP, БД, кэш
- ML: данные, обучение, артефакты
- Они развиваются независимо

## Структура

```
ml/
├── pyproject.toml              # torch, polars, lightgbm, xgboost, catboost, pytorch-geometric, scikit-learn
├── configs/
│   ├── base.yaml               # общие гиперпараметры
│   ├── synthetic.yaml          # под синтетику
│   ├── real.yaml               # под реальные данные
│   └── machines/
│       ├── rtx5060.yaml
│       └── rtx4070_12gb.yaml
├── transit_ai/
│   ├── data/
│   │   ├── base.py             # ABC DataSource
│   │   ├── synthetic.py        # генератор 800 остановок, 40 маршрутов, 2 года
│   │   ├── real.py             # адаптер под реальные данные
│   │   ├── validators.py       # контракты
│   │   ├── features.py         # фичеинжиниринг
│   │   └── schemas.py          # parquet schema для predictions
│   ├── models/
│   │   ├── base.py             # ABC Predictor (load, predict, train, save)
│   │   ├── baseline.py
│   │   ├── xgboost_pred.py
│   │   ├── gru.py              # адаптация contest/.../experiment_neural_gru.py
│   │   └── hybrid.py           # адаптация experiment_blend_gru_lgbm.py
│   ├── training/
│   │   ├── train.py
│   │   ├── predict.py
│   │   ├── evaluate.py
│   │   ├── calibrate.py        # per-bucket (из apply_bucket_calibration.py)
│   │   └── registry.py         # ModelRegistry (save → meta.json + model.pkl)
│   ├── montecarlo/             # копия из ~/Repositories/montecarlo/
│   │   ├── simulator.py
│   │   ├── distributions.py
│   │   └── cli.py
│   └── reports/
│       ├── metrics.py
│       └── plots.py            # matplotlib для evaluate
├── scripts/
│   ├── gen_synthetic.py        # → data/synthetic/
│   ├── train_baseline.py
│   ├── train_xgboost.py
│   ├── train_gru.py
│   ├── train_hybrid.py
│   ├── predict.py              # → predictions/*.parquet
│   ├── calibrate.py            # обновляет predictions
│   ├── evaluate.py             # → reports/
│   ├── inventory.py            # → data/validation_reports/inventory.json
│   ├── sweep.py                # гиперпараметры
│   └── monte_carlo_scenario.py # → predictions/*_mc.parquet
├── notebooks/
│   ├── 01_eda_synthetic.ipynb
│   ├── 02_gru_experiments.ipynb
│   └── 03_validate_real.ipynb
├── artifacts/                  # .gitignore
│   └── baseline_v1/
│       ├── meta.json
│       ├── model.pkl
│       ├── preprocessor.pkl
│       └── calibration.json
└── tests/
    ├── test_predictor_contract.py
    ├── test_synthetic.py
    ├── test_validators.py
    └── test_calibration.py
```

## Контракт с API

API читает артефакты через `apps/backend/forecast/loader.py`:

```python
import json
import jsonschema
from pathlib import Path
from jsonschema import validate

SCHEMA = json.loads(Path("docs/schemas/prediction_artifact.schema.json").read_text())

class ArtifactLoader:
    def __init__(self, artifacts_dir: Path):
        self.dir = artifacts_dir

    def load(self, model_id: str) -> ModelArtifact:
        meta_path = self.dir / model_id / "meta.json"
        meta = json.loads(meta_path.read_text())
        jsonschema.validate(meta, SCHEMA)  # падает с понятной ошибкой если невалидно
        model = self._load_model(meta["files"]["model"])
        return ModelArtifact(meta=meta, model=model, ...)
```

## Переключение модели

```bash
# Train
make train-xgboost

# Активировать (atomic symlink/rename)
python scripts/activate.py --model-id xgboost_v2

# API автоматически подхватит (reload registry)
curl http://localhost:8000/api/v1/models
```

В `apps/backend/forecast/registry.py`:

```python
class ModelRegistry:
    def __init__(self, artifacts_dir: Path):
        self.dir = artifacts_dir
        self.active_file = artifacts_dir / "active.json"
        self._cache = {}

    def get_active(self) -> ModelArtifact:
        active_id = json.loads(self.active_file.read_text())["model_id"]
        if active_id not in self._cache:
            self._cache[active_id] = ArtifactLoader(self.dir).load(active_id)
        return self._cache[active_id]

    def activate(self, model_id: str) -> None:
        # Validate first
        ArtifactLoader(self.dir).load(model_id)
        # Atomic write
        self.active_file.write_text(json.dumps({"model_id": model_id}))
        self._cache.clear()
```

## Машины

```bash
# На rtx5060 (8GB)
make train-gru

# На rtx4070 12GB (можно batch=512)
make train-gru MACHINE=rtx4070_12gb
```

`MACHINE` пробрасывается в `ml/configs/machines/<machine>.yaml` через `Makefile`.

## Что НЕ делаем

- ❌ Обучать модели в Docker
- ❌ Передавать model.pkl через HTTP
- ❌ Версионировать модели в git (только meta.json коммитим)
- ❌ Использовать pickle для unpickling непроверенных данных (security)
