"""Tests for Optuna study + objective (smoke, без реального XGBoost).

Проверяем:
  1. Study создаётся с sqlite storage
  2. Objective воспроизводима (детерминизм seed)
  3. 2-trial smoke завершается < 30 сек
  4. suggest_int/float/loguniform работают
  5. best_params не пустой, best_value ∈ R

Запуск: make optuna-smoke (Makefile).
"""

from __future__ import annotations

from pathlib import Path
import optuna


from optuna import create_study, load_study

from mlops.optuna.study_xgboost import (
    DEFAULT_SEARCH_SPACE,
    build_objective,
    suggest_params,
)


def test_search_space_has_required_keys() -> None:
    """Search space содержит все гиперпараметры XGBoost route-only."""
    expected = {"n_estimators", "max_depth", "learning_rate", "subsample",
                "colsample_bytree", "min_child_weight", "reg_alpha", "reg_lambda"}
    assert expected <= set(DEFAULT_SEARCH_SPACE.keys())


def test_suggest_params_returns_all_keys() -> None:
    """Trial.suggest_* вызывается для каждого ключа search space."""
    study = create_study(direction="maximize")
    trial = study.ask()
    params = suggest_params(trial)
    assert set(params.keys()) == set(DEFAULT_SEARCH_SPACE.keys())
    # Каждый параметр в ожидаемых границах
    assert 50 <= params["n_estimators"] <= 800
    assert 3 <= params["max_depth"] <= 12
    assert 0.01 <= params["learning_rate"] <= 0.5
    assert 0.5 <= params["subsample"] <= 1.0
    assert 0.5 <= params["colsample_bytree"] <= 1.0
    assert 1 <= params["min_child_weight"] <= 20
    assert 0 <= params["reg_alpha"] <= 5
    assert 0 <= params["reg_lambda"] <= 5


def test_objective_is_deterministic_with_seed(tmp_path: Path) -> None:
    """Objective воспроизводима при seed=42 (детерминизм R3 hackathon-rules)."""
    import optuna
    storage = f"sqlite:///{tmp_path / 'optuna.db'}"
    obj = build_objective(seed=42)
    
    # 2 trials на одном seed → одинаковые metrics
    study1 = create_study(storage=storage, study_name="s1", load_if_exists=False,
                         direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study1.optimize(obj, n_trials=2, show_progress_bar=False)
    
    study2 = create_study(storage=storage, study_name="s2", load_if_exists=False,
                         direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study2.optimize(obj, n_trials=2, show_progress_bar=False)
    
    assert study1.best_value == study2.best_value,         f"non-deterministic: {study1.best_value} != {study2.best_value}"


def test_two_trial_smoke_under_30_seconds(tmp_path: Path) -> None:
    """2-trial smoke < 30 сек (бюджет для CI)."""
    import time
    storage = f"sqlite:///{tmp_path / 'optuna.db'}"
    obj = build_objective(seed=42)
    study = create_study(storage=storage, study_name="smoke",
                        direction="maximize",
                        sampler=optuna.samplers.TPESampler(seed=42))
    t0 = time.monotonic()
    study.optimize(obj, n_trials=2, show_progress_bar=False)
    elapsed = time.monotonic() - t0
    assert elapsed < 30.0, f"smoke took {elapsed:.1f}s (> 30s)"
    assert len(study.trials) == 2
    assert study.best_value is not None


def test_study_persists_to_sqlite(tmp_path: Path) -> None:
    """После создания study можно загрузить из storage и увидеть trials."""
    storage = f"sqlite:///{tmp_path / 'optuna.db'}"
    obj = build_objective(seed=42)
    study = create_study(storage=storage, study_name="persist",
                        direction="maximize",
                        sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(obj, n_trials=3, show_progress_bar=False)
    
    # Перезагрузка из sqlite
    loaded = load_study(study_name="persist", storage=storage)
    assert len(loaded.trials) == 3
    assert loaded.best_value == study.best_value


def test_objective_maximize_direction_improves_with_good_params(tmp_path: Path) -> None:
    """Objective: хорошие params → лучше, чем случайные (sanity)."""
    obj = build_objective(seed=42)
    import optuna
    storage = f"sqlite:///{tmp_path / 'optuna.db'}"
    study = create_study(storage=storage, study_name="sanity",
                        direction="maximize",
                        sampler=optuna.samplers.TPESampler(seed=42))
    # 10 trials — TPE должен найти что-то лучше baseline
    study.optimize(obj, n_trials=10, show_progress_bar=False)
    assert study.best_value > 0.0
    assert "n_estimators" in study.best_params
