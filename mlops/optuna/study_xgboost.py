"""Optuna study for XGBoost route-only hyperparameter search.

Run:
    make optuna-smoke          # 2 trials, ~2 sec, smoke for CI
    make optuna-run            # 15 trials, R6 budget (timeout=1800s)

Storage: sqlite at mlops/optuna/studies/xgboost_route.db (gitignored).
Trials logged to MLflow as nested runs (see transit_ai.tracking).

Two objectives:
  - build_objective(seed): surrogate, deterministic, fast (for tests/CI).
  - build_real_objective(df_subset_path, seed): real XGBoost on a data subset.

Search space: 8 params (n_estimators, max_depth, learning_rate, subsample,
colsample_bytree, min_child_weight, reg_alpha, reg_lambda).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

import optuna

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE = f"sqlite:///{REPO_ROOT / 'mlops' / 'optuna' / 'studies' / 'xgboost_route.db'}"
DEFAULT_STUDY_NAME = "xgboost_route"


def _create_study(**kwargs: object) -> optuna.Study:
    """Wrapper around optuna.create_study to avoid name collision with
    the module-level create_study function below."""
    return optuna.create_study(**kwargs)


@dataclass(frozen=True)
class SearchSpace:
    """XGBoost route-only hyperparameter bounds."""

    n_estimators: tuple[int, int] = (50, 800)
    max_depth: tuple[int, int] = (3, 12)
    learning_rate: tuple[float, float] = (0.01, 0.5)
    subsample: tuple[float, float] = (0.5, 1.0)
    colsample_bytree: tuple[float, float] = (0.5, 1.0)
    min_child_weight: tuple[int, int] = (1, 20)
    reg_alpha: tuple[float, float] = (0.0, 5.0)
    reg_lambda: tuple[float, float] = (0.0, 5.0)

    def keys(self) -> list[str]:
        return list(self.__dataclass_fields__.keys())

    def items(self) -> list:
        return [(k, getattr(self, k)) for k in self.keys()]

    def __contains__(self, key: str) -> bool:
        return key in self.keys()


DEFAULT_SEARCH_SPACE = SearchSpace()


def suggest_params(trial: optuna.Trial, space: SearchSpace = DEFAULT_SEARCH_SPACE) -> dict[str, Any]:
    """Ask trial to suggest XGBoost hyperparameters."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", *space.n_estimators),
        "max_depth": trial.suggest_int("max_depth", *space.max_depth),
        "learning_rate": trial.suggest_float("learning_rate", *space.learning_rate, log=True),
        "subsample": trial.suggest_float("subsample", *space.subsample),
        "colsample_bytree": trial.suggest_float("colsample_bytree", *space.colsample_bytree),
        "min_child_weight": trial.suggest_int("min_child_weight", *space.min_child_weight),
        "reg_alpha": trial.suggest_float("reg_alpha", *space.reg_alpha),
        "reg_lambda": trial.suggest_float("reg_lambda", *space.reg_lambda),
    }


def _surrogate_score(params: dict[str, Any], seed: int) -> float:
    """Surrogate objective for smoke: deterministic function with single maximum.

    Mimics wape_score surface of real XGBoost:
      - Optimum: n_estimators=300, max_depth=6, learning_rate=0.05
      - Regularization lightly penalizes large values
      - Noise from seed for reproducibility (R3)

    Return range: [0, 1] (like WAPE-score).
    """
    target_n, target_d, target_lr = 300, 6, 0.05
    n_err = ((params["n_estimators"] - target_n) / 250) ** 2
    d_err = ((params["max_depth"] - target_d) / 4) ** 2
    lr_err = (params["learning_rate"] / target_lr - 1) ** 2
    sub_err = (params["subsample"] - 0.8) ** 2 * 4
    cs_err = (params["colsample_bytree"] - 0.8) ** 2 * 4
    mcw_err = (params["min_child_weight"] - 3) ** 2 / 100
    reg_err = (params["reg_alpha"] + params["reg_lambda"]) / 20

    base = 0.875 - 0.1 * (n_err + d_err + lr_err + sub_err + cs_err + mcw_err + reg_err)

    # Deterministic noise from seed+params (R3: reproducible)
    seed_bytes = hashlib.sha256(f"{seed}:{params}".encode()).digest()
    noise = (seed_bytes[0] - 128) / 10000.0

    return base + noise


def build_objective(
    seed: int = 42,
    real: bool = False,
) -> Callable[[optuna.Trial], float]:
    """Build objective function for Optuna.

    real=False (default): surrogate (fast, deterministic, for smoke/CI).
    real=True: stub that raises NotImplementedError; production needs
               transit_ai.models.xgboost_route integration.
    """
    if real:
        def real_objective(trial: optuna.Trial) -> float:
            raise NotImplementedError(
                "real=True requires transit_ai.models.xgboost_route; "
                "use real=False (surrogate) for smoke"
            )
        return real_objective

    def surrogate_objective(trial: optuna.Trial) -> float:
        params = suggest_params(trial)
        return _surrogate_score(params, seed)
    return surrogate_objective


def build_real_objective(
    df_subset_path: str | Path,
    seed: int = 42,
    n_estimators_cap: int = 300,
) -> Callable[[optuna.Trial], float]:
    """Real objective: train XGBoostRoutePredictor on df_subset, return holdout_wape_score.

    df_subset_path: parquet/csv with features+target (ready for XGBoostRoutePredictor.fit).
    seed: random seed for reproducibility.
    n_estimators_cap: safety cap (Optuna may suggest up to 800; we cap at 300 for R6).

    NOTE: requires xgboost + polars in PATH. For smoke, use build_objective (surrogate).
    """
    import time as _time  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415
    import polars as pl  # noqa: PLC0415

    from transit_ai.models.xgboost_route import XGBoostRoutePredictor  # noqa: PLC0415
    from transit_ai.reports.metrics import wape_score  # noqa: PLC0415

    df = pl.read_parquet(df_subset_path) if str(df_subset_path).endswith(".parquet") else pl.read_csv(df_subset_path)
    n = len(df)
    split = int(n * 0.8)
    train_df = df.head(split)
    val_df = df.tail(n - split)

    def real_objective(trial: optuna.Trial) -> float:
        params = suggest_params(trial)
        # Cap n_estimators for R6 budget
        n_est = min(params["n_estimators"], n_estimators_cap)
        t0 = _time.monotonic()
        predictor = XGBoostRoutePredictor(
            n_estimators=n_est,
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            subsample=params["subsample"],
            colsample_bytree=params["colsample_bytree"],
            min_child_weight=params["min_child_weight"],
            reg_alpha=params["reg_alpha"],
            reg_lambda=params["reg_lambda"],
            seed=seed,
        )
        predictor.fit(train_df)
        preds = predictor.predict_batch(val_df)
        actuals = val_df["boardings"].to_numpy()
        score = float(wape_score(actuals, np.asarray(preds)))
        elapsed = _time.monotonic() - t0
        trial.set_user_attr("train_time_sec", elapsed)
        return score
    return real_objective


def create_study(
    storage: str = DEFAULT_STORAGE,
    study_name: str = DEFAULT_STUDY_NAME,
    n_trials: int = 15,
    seed: int = 42,
    timeout: float | None = 1800.0,
) -> optuna.Study:
    """Create study, optimize n_trials with TPE sampler.

    Resumable: if study with same name exists in storage, continues from
    last trial count.
    """
    Path(storage.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = _create_study(
        storage=storage,
        study_name=study_name,
        direction="maximize",
        sampler=sampler,
        load_if_exists=True,
    )
    obj = build_objective(seed=seed)
    study.optimize(obj, n_trials=n_trials, timeout=timeout, show_progress_bar=False)
    return study


__all__ = [
    "DEFAULT_SEARCH_SPACE",
    "DEFAULT_STORAGE",
    "DEFAULT_STUDY_NAME",
    "SearchSpace",
    "build_objective",
    "build_real_objective",
    "create_study",
    "suggest_params",
]
