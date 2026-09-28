"""Local conftest для mlops/tests: корень репозитория → sys.path.

Зачем: mlops-тесты — изолированная лаборатория (clinerule 33). Они НЕ должны
попадать в `make test` (ml/tests), потому что требуют эфемерных зависимостей
(optuna / dvc / apache-airflow) и сети. Запуск — только через
`make mlops-test` / `make optuna-test` / `make dvc-test` / `make airflow-test`.

Этот conftest добавляет корень репо в sys.path, чтобы работали импорты
`from mlops.optuna.study_xgboost import ...` при запуске pytest из любого каталога.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
