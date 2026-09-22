"""Prediction pipeline (T-033).

Контракт:
    predict(PredictConfig) → Path к predictions/<date>_<model_id>.parquet

Pipeline:
1. Resolve model_id: cfg.model_id → ModelRegistry.get_active_id() если None
2. ModelRegistry.load(model_id) → fitted Predictor
3. Discover stop_ids: cfg.stop_ids если задан, иначе fallback [1..10]
4. Load calibration.json (если есть) — per-bucket bias (T-034)
5. Итерируем stop_ids × periods внутри [cfg.from_dt, cfg.to_dt]
6. Predictor.predict(stop_id, ...) → list[PredictionPoint]
7. Calibration adjustment в log-space (если calibration есть)
8. Write parquet с schema из docs/schemas/predictions.schema.json

References:
- docs/schemas/predictions.schema.json
- ml/transit_ai/data/schemas.py
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from transit_ai.training.registry import ModelRegistry

logger = logging.getLogger("predict")

DEFAULT_HORIZON = "day"
DEFAULT_GRANULARITY = "hour"
DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "ml" / "artifacts"
DEFAULT_PREDICTIONS_DIR = Path(__file__).resolve().parents[3] / "predictions"
HORIZON_HOURS: dict[str, int] = {"day": 24, "month": 24 * 30, "year": 24 * 365}


def default_artifacts_dir() -> Path:
    env = os.environ.get("TRANSIT_AI_ARTIFACTS_DIR")
    return Path(env) if env else DEFAULT_ARTIFACTS_DIR


def default_predictions_dir() -> Path:
    env = os.environ.get("TRANSIT_AI_PREDICTIONS_DIR")
    return Path(env) if env else DEFAULT_PREDICTIONS_DIR


@dataclass(frozen=True)
class PredictConfig:
    """Immutable prediction config (T-033)."""

    artifacts_dir: Path = field(default_factory=default_artifacts_dir)
    output_dir: Path = field(default_factory=default_predictions_dir)
    model_id: str | None = None
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    horizon: str = DEFAULT_HORIZON
    granularity: str = DEFAULT_GRANULARITY
    stop_ids: list[int] = field(default_factory=list)
    scenario_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.artifacts_dir, Path):
            object.__setattr__(self, "artifacts_dir", Path(self.artifacts_dir))
        if not isinstance(self.output_dir, Path):
            object.__setattr__(self, "output_dir", Path(self.output_dir))
        if self.horizon not in HORIZON_HOURS:
            raise ValueError(
                f"horizon must be one of {list(HORIZON_HOURS)}, got {self.horizon!r}"
            )
        if self.granularity not in ("hour", "day", "month"):
            raise ValueError(
                f"granularity must be one of (hour, day, month), got {self.granularity!r}"
            )

    def resolve_window(self) -> tuple[datetime, datetime]:
        """Resolve [from_dt, to_dt] using now + horizon as defaults."""
        if (self.from_dt is None) != (self.to_dt is None):
            raise ValueError(
                "from_dt and to_dt must both be set or both be None "
                f"(got from_dt={self.from_dt}, to_dt={self.to_dt})"
            )
        if self.from_dt is None:
            now = datetime.now(UTC).replace(microsecond=0, tzinfo=None)
            end = now + timedelta(hours=HORIZON_HOURS[self.horizon])
            return now, end
        # Both are non-None at this point (guarded by first check)
        return self.from_dt, self.to_dt  # type: ignore[return-value]


def _load_calibration(artifacts_dir: Path, model_id: str) -> dict[str, Any] | None:
    path = artifacts_dir / model_id / "calibration.json"
    if not path.is_file():
        return None
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return raw


def _bucket_bias(
    stop_id: int, period_start: datetime, calib: dict[str, Any] | None
) -> float:
    """Return per-bucket bias for (stop_id, weekday, hour)."""
    if not calib:
        return 0.0
    bucket_count = len(calib.get("biases", []))
    if bucket_count == 0:
        return float(calib.get("global_bias", 0.0))
    bucket = (stop_id, period_start.weekday(), period_start.hour)
    idx = hash(bucket) % bucket_count
    return float(calib["biases"][idx])


def _apply_calibration(value: float, bias: float) -> float:
    """Log-space adjustment: value_calibrated = exp(log(1+value) + bias) - 1."""
    if value <= 0:
        return 0.0
    return float(np.expm1(np.log1p(value) + bias))


def _resolve_stop_ids(cfg: PredictConfig) -> list[int]:
    """Resolve stop_ids: explicit list, else fallback [1..10]."""
    if cfg.stop_ids:
        return sorted({int(s) for s in cfg.stop_ids})
    return list(range(1, 11))


def predict(cfg: PredictConfig) -> Path:
    """Run prediction pipeline; write parquet; return output path."""
    registry = ModelRegistry(cfg.artifacts_dir)
    model_id = cfg.model_id or registry.get_active_id()
    if not model_id:
        raise FileNotFoundError(
            f"No model_id given and {cfg.artifacts_dir / 'active.json'} missing"
        )

    predictor = registry.load(model_id)
    logger.info(
        f"Predicting with {model_id!r} (kind={predictor.kind!r}) "
        f"horizon={cfg.horizon!r} granularity={cfg.granularity!r}"
    )

    from_dt, to_dt = cfg.resolve_window()
    stop_ids = _resolve_stop_ids(cfg)

    calibration = _load_calibration(cfg.artifacts_dir, model_id)

    delta: timedelta
    if cfg.granularity == "hour":
        delta = timedelta(hours=1)
    elif cfg.granularity == "day":
        delta = timedelta(days=1)
    else:
        delta = timedelta(days=30)

    rows: list[dict[str, Any]] = []
    cur = from_dt
    while cur < to_dt:
        next_dt = cur + delta
        for stop_id in stop_ids:
            pts = predictor.predict(stop_id, cur, next_dt)
            for pp in pts:
                adjusted_value = pp.value
                if calibration:
                    bias = _bucket_bias(stop_id, pp.period_start, calibration)
                    adjusted_value = _apply_calibration(pp.value, bias)
                rows.append(
                    {
                        "period_start": pp.period_start,
                        "period_end": pp.period_end,
                        "stop_id": int(pp.stop_id),
                        "route_id": int(pp.route_id)
                        if pp.route_id is not None
                        else None,
                        "value": float(max(adjusted_value, 0.0)),
                        "lower": float(max(pp.lower, 0.0)),
                        "upper": float(max(pp.upper, 0.0)),
                        "horizon": cfg.horizon,
                        "granularity": cfg.granularity,
                        "model_id": model_id,
                        "scenario_id": cfg.scenario_id,
                    }
                )
        cur = next_dt

    if not rows:
        raise RuntimeError(
            f"No predictions produced for model_id={model_id!r} from {from_dt} to {to_dt}"
        )

    df = pd.DataFrame(rows)
    arrow_schema = pa.schema(
        [
            pa.field("period_start", pa.timestamp("ns")),
            pa.field("period_end", pa.timestamp("ns")),
            pa.field("stop_id", pa.int64()),
            pa.field("route_id", pa.int64()),
            pa.field("value", pa.float64()),
            pa.field("lower", pa.float64()),
            pa.field("upper", pa.float64()),
            pa.field("horizon", pa.string()),
            pa.field("granularity", pa.string()),
            pa.field("model_id", pa.string()),
            pa.field("scenario_id", pa.string()),
        ]
    )

    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    out_path = (
        cfg.output_dir
        / f"predictions_{from_dt.strftime('%Y-%m-%d')}_{model_id}_{ts}.parquet"
    )

    table = pa.Table.from_pandas(df, schema=arrow_schema, preserve_index=False)
    pq.write_table(table, out_path, compression="snappy")
    logger.info(
        f"✅ Wrote {len(df)} predictions → {out_path} "
        f"({df['stop_id'].nunique()} stops × "
        f"{len(df) // max(df['stop_id'].nunique(), 1)} periods)"
    )
    return out_path


__all__ = [
    "DEFAULT_ARTIFACTS_DIR",
    "DEFAULT_GRANULARITY",
    "DEFAULT_HORIZON",
    "DEFAULT_PREDICTIONS_DIR",
    "HORIZON_HOURS",
    "PredictConfig",
    "default_artifacts_dir",
    "default_predictions_dir",
    "predict",
]
