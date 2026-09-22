"""Universal training entry point (T-032).

Контракт:
    train_model(predictor_cls, config) → SaveResult

Pipeline:
1. Load synthetic ridership via DataSource (data-agnostic, future RealSource)
2. Instantiate predictor_cls(**hyperparams)
3. predictor.fit(ridership_df)
4. ModelRegistry.save(predictor, ...)
5. (опционально) ModelRegistry.activate(model_id)

Используется для:
- BaselineMean (T-032, scripts/train_baseline.py)
- XGBoostPredictor (T-032, scripts/train_xgboost.py — будущее)
- GRU, Hybrid (T-029, T-030 — будущее)
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from transit_ai.data.base import DataSource, DateRange
from transit_ai.data.synthetic import SyntheticConfig, SyntheticSource
from transit_ai.models.base import Predictor
from transit_ai.training.registry import (
    ModelRegistry,
    SaveResult,
    git_commit,
    hash_dataframe,
)

logger = logging.getLogger("train")

#: Default training history length (28 days) + holdout (7 days) = 35.
DEFAULT_N_DAYS = 35

#: Default synthetic seed (R6 reproducibility across runs).
DEFAULT_SEED = 42

#: Default artifacts dir; override через TRANSIT_AI_ARTIFACTS_DIR env.
DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


def default_artifacts_dir() -> Path:
    """Resolve artifacts dir: env var → default."""
    env = os.environ.get("TRANSIT_AI_ARTIFACTS_DIR")
    return Path(env) if env else DEFAULT_ARTIFACTS_DIR


@dataclass(frozen=True)
class TrainConfig:
    """Immutable training configuration. All defaults match Makefile flags (T-032)."""

    n_days: int = DEFAULT_N_DAYS
    seed: int = DEFAULT_SEED
    model_id: str = "baseline_v1"
    version: str = "v0.1.0"
    horizons: tuple[str, ...] = ("day",)
    granularities: tuple[str, ...] = ("hour",)
    hyperparams: dict[str, Any] = field(default_factory=dict)
    artifacts_dir: Path = field(default_factory=default_artifacts_dir)
    activate: bool = True
    data_source_factory: Callable[[TrainConfig], DataSource] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.artifacts_dir, Path):
            object.__setattr__(self, "artifacts_dir", Path(self.artifacts_dir))


def _make_default_data_source(cfg: TrainConfig) -> DataSource:
    """Default DataSource: SyntheticSource with seed + n_days."""
    return SyntheticSource(SyntheticConfig(n_days=cfg.n_days, seed=cfg.seed))


def _instantiate_predictor(
    predictor_cls: type[Predictor], cfg: TrainConfig
) -> Predictor:
    """Create predictor instance with hyperparams passed as kwargs to __init__.

    Raises:
        TypeError: если predictor_cls не subclass Predictor.
    """
    if not (isinstance(predictor_cls, type) and issubclass(predictor_cls, Predictor)):
        raise TypeError(
            f"predictor_cls must be a Predictor subclass, got {predictor_cls!r}"
        )
    return predictor_cls(**cfg.hyperparams)


def _load_ridership(cfg: TrainConfig) -> pd.DataFrame:
    """Generate/load ridership via data source factory."""
    factory = cfg.data_source_factory or _make_default_data_source
    source = factory(cfg)
    epoch = datetime(2026, 1, 1)  # noqa: DTZ001 — SyntheticSource сравнивает tz-naive
    return source.load_ridership(
        DateRange(epoch, epoch + timedelta(days=cfg.n_days - 1))
    )


def train_model(
    predictor_cls: type[Predictor],
    cfg: TrainConfig,
) -> SaveResult:
    """Universal training entry: fit → save → (activate).

    Args:
        predictor_cls: Predictor subclass (BaselineMean, XGBoostPredictor, ...).
        cfg: TrainConfig with n_days, seed, model_id, hyperparams, etc.

    Returns:
        SaveResult from ModelRegistry.save (artifact_dir + validated meta dict).
    """
    logger.info(
        f"Training {predictor_cls.__name__} (model_id={cfg.model_id!r}, "
        f"n_days={cfg.n_days}, seed={cfg.seed})"
    )

    ridership_df = _load_ridership(cfg)
    if ridership_df.empty:
        raise ValueError("Loaded ridership is empty; check DataSource config.")
    train_data_hash = hash_dataframe(ridership_df)

    predictor = _instantiate_predictor(predictor_cls, cfg)
    # model_id comes from the predictor itself (cfg.hyperparams['model_id'] if passed,
    # else the predictor class default). This way registry.save() and registry.activate()
    # always agree — no risk of mismatched paths.
    effective_model_id = getattr(predictor, "model_id", None) or cfg.model_id
    predictor.fit(ridership_df)

    if not getattr(predictor, "fitted_", False):
        raise ValueError(f"{predictor_cls.__name__}.fit() did not set fitted_=True")

    registry = ModelRegistry(cfg.artifacts_dir)
    result = registry.save(
        predictor,
        version=cfg.version,
        train_data_hash=train_data_hash,
        seed=cfg.seed,
        horizons=cfg.horizons,
        granularities=cfg.granularities,
        git_sha=git_commit(),
    )

    if cfg.activate:
        registry.activate(effective_model_id)
        logger.info(f"✅ Activated {effective_model_id!r} (active.json updated)")

    logger.info(
        f"✅ Trained {effective_model_id!r}: {result.meta.get('model_id', '?')} "
        f"(kind={result.meta.get('kind', '?')}) → {result.artifact_dir}"
    )
    return result


__all__ = [
    "DEFAULT_ARTIFACTS_DIR",
    "DEFAULT_N_DAYS",
    "DEFAULT_SEED",
    "TrainConfig",
    "default_artifacts_dir",
    "train_model",
]
