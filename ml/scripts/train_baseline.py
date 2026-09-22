#!/usr/bin/env python3
"""CLI: train BaselineMean on synthetic ridership (T-032).

Usage:
    make train-baseline
    uv run --directory ml python scripts/train_baseline.py [--n-days 35] [--seed 42] [--model-id baseline_v1]

Output:
    - ml/artifacts/<model_id>/meta.json (validates against prediction_artifact.schema.json)
    - ml/artifacts/<model_id>/model.pkl
    - ml/artifacts/active.json → {"model_id": <model_id>}

Override artifacts location via $TRANSIT_AI_ARTIFACTS_DIR (used by tests).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from transit_ai.models.baseline import BaselineMean
from transit_ai.training.train import TrainConfig, train_model

logger = logging.getLogger("train_baseline")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml_config(path: Path) -> dict:
    """Load YAML config file (optional)."""
    if not path.is_file():
        print(f"❌ Config file not found: {path}", file=sys.stderr)
        sys.exit(2)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        print(
            f"❌ Config must be a YAML mapping, got {type(cfg).__name__}",
            file=sys.stderr,
        )
        sys.exit(2)
    return cfg


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--n-days", type=int, default=35, help="Synthetic data days (default: 35)"
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    p.add_argument(
        "--model-id", default="baseline_v1", help="Artifact ID (default: baseline_v1)"
    )
    p.add_argument("--version", default="v0.1.0", help="Semver (default: v0.1.0)")
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional YAML config file (overrides CLI defaults except explicit flags).",
    )
    p.add_argument(
        "--no-activate",
        action="store_true",
        help="Don't update active.json (useful for offline training).",
    )
    p.add_argument(
        "--hyperparam",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override hyperparameter (repeatable, e.g. --hyperparam window=7).",
    )
    args = p.parse_args()

    # Parse --hyperparam k=v into dict
    hyperparams: dict[str, object] = {}
    for kv in args.hyperparam:
        if "=" not in kv:
            print(f"❌ --hyperparam expects KEY=VALUE, got {kv!r}", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        # Try int → float → str (same heuristic as catboost/lightgbm CLI)
        try:
            hyperparams[k] = int(v)
        except ValueError:
            try:
                hyperparams[k] = float(v)
            except ValueError:
                hyperparams[k] = v

    # CLI --model-id wins over both YAML model_id and predictor class default.
    # It is propagated as a hyperparam so the predictor's own model_id field reflects it,
    # ensuring registry.save() and registry.activate() use the same id.
    hyperparams["model_id"] = args.model_id

    # Start with YAML config if provided (lower priority than CLI flags for explicit fields)
    yaml_cfg: dict = {}
    if args.config is not None:
        yaml_cfg = _load_yaml_config(args.config)
        # Apply YAML-level hyperparams if not overridden by --hyperparam
        yaml_hp = yaml_cfg.get("hyperparams", {}) or {}
        for k, v in yaml_hp.items():
            hyperparams.setdefault(k, v)

    cfg = TrainConfig(
        n_days=args.n_days,
        seed=args.seed,
        model_id=args.model_id,
        version=args.version,
        horizons=tuple(yaml_cfg.get("horizons", ["day"])),
        granularities=tuple(yaml_cfg.get("granularities", ["hour"])),
        hyperparams=hyperparams,
        activate=not args.no_activate,
    )

    print(
        f"📦 Training BaselineMean: model_id={cfg.model_id!r}, "
        f"n_days={cfg.n_days}, seed={cfg.seed}, hyperparams={hyperparams}"
    )

    try:
        train_model(BaselineMean, cfg)
    except (ValueError, TypeError, FileNotFoundError) as e:
        print(f"❌ Training failed: {e}", file=sys.stderr)
        return 1

    print()
    print(f"  artifact = {cfg.artifacts_dir / cfg.model_id}")
    print(f"  meta.json = {(cfg.artifacts_dir / cfg.model_id / 'meta.json')}")
    if cfg.activate:
        print(f"  active.json = {cfg.artifacts_dir / 'active.json'}")
    print("\n✅ Done. Next: make evaluate   или   make predict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
