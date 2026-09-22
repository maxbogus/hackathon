"""Per-bucket bias calibration pipeline (T-034).

Контракт:
    fit_calibration(CalibrateConfig) → Calibration

Pipeline:
1. Load holdout: parquet with (y_true, y_pred, stop_id, timestamp)
2. Group by (stop_id, weekday, hour) bucket → bias_per_bucket = mean(log(y_true+1) - log(y_pred+1))
3. Shrinkage: alpha = n_obs / (n_obs + prior); bias_eff = alpha * bias_bucket + (1-alpha) * global_bias
4. Save to ml/artifacts/<model_id>/calibration.json: {kind, biases, edges, global_bias, prior, n_obs}
5. predict.py (T-033) при наличии calibration.json корректирует values в log-space.

References:
- ~/Repositories/contest/ecup26-user-value/scripts/apply_bucket_calibration.py (D-005)
- prediction_artifact.schema.json (calibration field)
- ml/transit_ai/training/predict.py (consumer)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("calibrate")


DEFAULT_PRIOR = 100.0
DEFAULT_MIN_OBS_PER_BUCKET = 5
DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "ml" / "artifacts"


def default_artifacts_dir() -> Path:
    env = os.environ.get("TRANSIT_AI_ARTIFACTS_DIR")
    return Path(env) if env else DEFAULT_ARTIFACTS_DIR


@dataclass(frozen=True)
class Calibration:
    """Calibration payload (in-memory)."""

    kind: str
    biases_per_bucket: dict[tuple[int, int, int], float]
    edges: list[float]
    global_bias: float
    prior: float
    n_obs: int

    def __len__(self) -> int:
        return len(self.biases_per_bucket)

    def to_dict(self) -> dict[str, object]:
        """Serialise for artifact + JSON."""
        biases_list = [
            self.biases_per_bucket[k] for k in sorted(self.biases_per_bucket)
        ]
        return {
            "kind": self.kind,
            "edges": self.edges,
            "biases": biases_list,
            "global_bias": self.global_bias,
            "prior": self.prior,
            "n_obs": self.n_obs,
            "buckets": [
                {"stop_id": k[0], "weekday": k[1], "hour": k[2], "bias": v}
                for k, v in sorted(self.biases_per_bucket.items())
            ],
        }


@dataclass(frozen=True)
class CalibrateConfig:
    """Immutable fit config."""

    artifacts_dir: Path = field(default_factory=default_artifacts_dir)
    model_id: str | None = None  # None → read active.json
    holdout_parquet: Path | None = None  # if None → use last 7 days of synthetic
    prior: float = DEFAULT_PRIOR
    min_obs_per_bucket: int = DEFAULT_MIN_OBS_PER_BUCKET

    def __post_init__(self) -> None:
        if not isinstance(self.artifacts_dir, Path):
            object.__setattr__(self, "artifacts_dir", Path(self.artifacts_dir))
        if self.holdout_parquet is not None and not isinstance(
            self.holdout_parquet, Path
        ):
            object.__setattr__(self, "holdout_parquet", Path(self.holdout_parquet))


def apply_calibration(value: float, bias: float) -> float:
    """Apply bias in log-space.

    value_calibrated = exp(log(1 + value) + bias) - 1
    If value <= 0 → 0 (log undefined).
    """
    if value <= 0:
        return 0.0
    return float(np.expm1(np.log1p(value) + bias))


def compute_bucket_biases(
    holdout_df: pd.DataFrame,
    prior: float = DEFAULT_PRIOR,
    min_obs_per_bucket: int = DEFAULT_MIN_OBS_PER_BUCKET,
) -> Calibration:
    """Compute per-bucket bias with shrinkage."""
    if holdout_df.empty:
        raise ValueError("holdout_df is empty")

    df = holdout_df.copy()
    df["weekday"] = pd.to_datetime(df["timestamp"]).dt.weekday
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    df["log_y_true"] = np.log1p(df["y_true"].clip(lower=0))
    df["log_y_pred"] = np.log1p(df["y_pred"].clip(lower=0))
    df["log_residual"] = df["log_y_true"] - df["log_y_pred"]

    global_bias = float(df["log_residual"].mean())
    n_total = len(df)

    grouped = (
        df.groupby(["stop_id", "weekday", "hour"])["log_residual"]
        .agg(bias_raw="mean", n_obs="size")
        .reset_index()
    )

    biases: dict[tuple[int, int, int], float] = {}
    edges: list[float] = []
    for row in grouped.itertuples(index=False):
        n = int(row.n_obs)
        bias_raw = float(row.bias_raw)
        if n < min_obs_per_bucket:
            # Skip unreliable bucket — global will be used instead.
            continue
        alpha = n / (n + prior)
        bias_eff = alpha * bias_raw + (1 - alpha) * global_bias
        key = (int(row.stop_id), int(row.weekday), int(row.hour))
        biases[key] = bias_eff

    # Sort biases to match edges for array form
    if biases:
        sorted_keys = sorted(biases)
        biases_per_idx = [biases[k] for k in sorted_keys]
        edges = [0.0, len(biases_per_idx)]
    else:
        biases_per_idx = []
        edges = [0.0]

    return Calibration(
        kind="bucket",
        biases_per_bucket=biases,
        edges=edges,
        global_bias=global_bias,
        prior=prior,
        n_obs=n_total,
    )


def fit_calibration(config: CalibrateConfig) -> Calibration | None:
    """Fit per-bucket biases and save calibration.json. Returns Calibration or None."""
    from transit_ai.training.registry import ModelRegistry

    if config.holdout_parquet is None or not config.holdout_parquet.is_file():
        raise FileNotFoundError(
            f"holdout parquet not found: {config.holdout_parquet}. "
            "Generate via evaluate.py (T-035) before calibrating."
        )

    holdout_df = pd.read_parquet(config.holdout_parquet)
    calib = compute_bucket_biases(
        holdout_df, prior=config.prior, min_obs_per_bucket=config.min_obs_per_bucket
    )

    registry = ModelRegistry(config.artifacts_dir)
    model_id = config.model_id or registry.get_active_id()
    if not model_id:
        raise FileNotFoundError(
            f"No model_id given and {config.artifacts_dir / 'active.json'} missing"
        )

    artifact_dir = config.artifacts_dir / model_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    calib_path = artifact_dir / "calibration.json"
    payload = calib.to_dict()
    calib_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info(
        f"✅ Fitted calibration for {model_id!r}: "
        f"{len(calib.biases_per_bucket)} buckets, "
        f"n_obs={calib.n_obs}, prior={calib.prior}, "
        f"global_bias={calib.global_bias:.4f}"
    )
    logger.info(f"   → {calib_path}")
    return calib


__all__ = [
    "DEFAULT_ARTIFACTS_DIR",
    "DEFAULT_MIN_OBS_PER_BUCKET",
    "DEFAULT_PRIOR",
    "CalibrateConfig",
    "Calibration",
    "apply_calibration",
    "compute_bucket_biases",
    "default_artifacts_dir",
    "fit_calibration",
]
