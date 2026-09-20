"""BenchmarkConfig + BenchmarkResult dataclasses.

Контракт: каждая BenchmarkResult содержит seed, git_commit, train_data_hash
для воспроизводимости (R6 hackathon-rules).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkConfig:
    """Single experiment config: model + features + hyperparams + cv params."""

    model_id: str                           # "baseline_v1", "xgboost_v2", "gru_v1"
    feature_set: str = "minimal"            # "minimal" | "extended" | "all"
    hyperparams: dict[str, Any] = field(default_factory=dict)
    cv_folds: int = 4
    seed: int = 42
    horizons: tuple[str, ...] = ("day", "month")  # ("day", "month", "year")

    def config_hash(self) -> str:
        """Stable hash of the config (for reproducibility tracking)."""
        d = asdict(self)
        d["horizons"] = list(d["horizons"])
        return hashlib.sha256(
            json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]


@dataclass
class BenchmarkResult:
    """Single experiment result: metrics + per-fold scores + provenance."""

    config: BenchmarkConfig
    metrics: dict[str, float]              # {"rmsle": 0.42, "mae": 12.3, "mape": 0.18}
    fold_scores: list[float]               # per-fold RMSLE
    train_time_sec: float = 0.0
    git_commit: str = "unknown"
    train_data_hash: str = "unknown"
    timestamp: str = ""                    # ISO-8601 UTC
    notes: str = ""                        # human-readable comment

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize for JSON report (tuple → list, dataclass → dict)."""
        d = asdict(self)
        d["config"]["horizons"] = list(self.config.horizons)
        return d


# Preset configs (curated coordinate-style, not full grid)
PRESET_CONFIGS: list[BenchmarkConfig] = [
    BenchmarkConfig(
        model_id="baseline_v1",
        feature_set="minimal",
        hyperparams={"window": 7},
        cv_folds=4,
    ),
    BenchmarkConfig(
        model_id="xgboost_v1",
        feature_set="minimal",
        hyperparams={"n_estimators": 200, "max_depth": 6, "learning_rate": 0.05},
        cv_folds=4,
    ),
    BenchmarkConfig(
        model_id="xgboost_v1",
        feature_set="extended",
        hyperparams={"n_estimators": 500, "max_depth": 8, "learning_rate": 0.03},
        cv_folds=4,
    ),
    BenchmarkConfig(
        model_id="gru_v1",
        feature_set="extended",
        hyperparams={"hidden_dim": 64, "num_layers": 2, "dropout": 0.2, "epochs": 30},
        cv_folds=4,
    ),
]
