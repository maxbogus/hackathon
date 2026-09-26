#!/usr/bin/env python3
"""T-177-GRU-SWEEP: parameter sweep for GRU (по шаблону contest sweep_neural.py).

Grid из 7 configs по (hidden, layers, lr, seq_len, epochs). Interrupt-safe:
`docs/reports/gru_sweep_<date>.csv` — source of truth, resume через load_done().

Usage:
    uv run --directory ml python scripts/sweep_gru.py [--quick] [--output PATH]

    --quick  : только первые 3 configs (~10 сек на GPU)
    --output : путь к CSV (default: docs/reports/gru_sweep_<YYYY-MM-DD>.csv)

Refs:
    contest/ecup26-user-value/scripts/sweep_neural.py (interrupt-safe grid)
    F-064: GRU v2_extended (single config) не улучшает XGBoost (WAPE 0.13)
"""

from __future__ import annotations

import argparse
import csv
import datetime
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("/home/maxbogus/Repositories/hackathon")
ML_DIR = REPO_ROOT / "ml"
REPORTS_DIR = REPO_ROOT / "docs" / "reports"

#: Grid (kind, hidden, layers, lr, seq_len, epochs).
#: По шаблону contest sweep_neural.py: 4 базовых configs + 3 для проверки гипотез.
GRID: list[tuple[str, int, int, float, int, int]] = [
    ("gru", 64, 1, 3e-4, 168, 15),  # contest baseline + наш v1
    ("gru", 128, 2, 3e-4, 336, 20),  # наш v2_extended (F-064)
    ("gru", 128, 3, 3e-4, 336, 20),  # deeper: больше слоёв > 2?
    ("gru", 256, 2, 3e-4, 336, 20),  # wider: больше hidden > 128?
    ("gru", 128, 2, 3e-4, 720, 20),  # bigger window (30d)
    ("gru", 64, 2, 3e-4, 504, 20),  # smaller + wider window
    ("gru", 192, 2, 3e-4, 336, 20),  # mid-width sweep
]


def _append_row(out: Path, row: str) -> None:
    """Append a single CSV row (interrupt-safe)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fh:
        fh.write(row + "\n")


def load_done(out: Path) -> set[tuple[str, int, int, float, int]]:
    """Read done configs from CSV. Skip FAIL/TIMEOUT (можно перезапустить)."""
    done: set[tuple[str, int, int, float, int]] = set()
    if not out.exists():
        return done
    with out.open() as fh:
        reader = csv.reader(fh)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) < 6:
                continue
            try:
                kind, hidden, layers, lr, seq_len = row[:5]
                wape = row[6] if len(row) > 6 else "FAIL"
                if wape in ("FAIL", "TIMEOUT", ""):
                    continue
                done.add((kind, int(hidden), int(layers), float(lr), int(seq_len)))
            except (ValueError, IndexError):
                continue
    return done


def run_one_config(
    kind: str,
    hidden: int,
    layers: int,
    lr: float,
    seq_len: int,
    epochs: int,
) -> tuple[float, int]:
    """Run one GRU config via subprocess, return (wape_score, best_epoch)."""
    # cwd=ML_DIR — uv видит scripts/train_gru.py и venv в ml/.pyproject.toml
    cmd = [
        "uv",
        "run",
        "python",
        "scripts/train_gru.py",
        "--start-date",
        "2025-01-01",
        "--end-date",
        "2025-10-31",
        "--model-id",
        f"sweep_{kind}_h{hidden}_l{layers}_w{seq_len}_e{epochs}",
        "--seq-len",
        str(seq_len),
        "--hidden",
        str(hidden),
        "--layers",
        str(layers),
        "--epochs",
        str(epochs),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, cwd=str(ML_DIR)
        )
    except subprocess.TimeoutExpired:
        return float("nan"), 0
    # Regex matches BOTH formats:
    #   "Holdout WAPE-score (сен-окт, GRU): 0.1830"
    #   "Holdout WAPE-score = 0.1830"
    # Берём последнее вхождение (финальный score после calibration).
    matches = re.findall(r"Holdout WAPE-score[^:=]*[:=]\s*(\d+\.\d+)", result.stdout)
    if matches:
        return float(matches[-1]), epochs
    return float("nan"), 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--quick", action="store_true", help="Только первые 3 configs")
    ap.add_argument("--output", type=str, default=None, help="Путь к CSV")
    args = ap.parse_args()

    grid = GRID[:3] if args.quick else GRID
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    out = Path(args.output) if args.output else (REPORTS_DIR / f"gru_sweep_{today}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    if not out.exists():
        _append_row(
            out,
            "kind,hidden,layers,lr,seq_len,epochs,wape_score,best_epoch,date,saved",
        )

    done = load_done(out)
    todo = [c for c in grid if (c[0], c[1], c[2], c[3], c[4]) not in done]
    print(
        f"resume: {len(done)} done, {len(todo)} remaining of {len(grid)} total",
        flush=True,
    )

    for i, (kind, h, lay, lr, w, ep) in enumerate(todo, start=1):
        t0 = datetime.datetime.now().strftime("%H:%M:%S")
        print(
            f"[{i}/{len(todo)}] {kind} h={h} l={lay} lr={lr} w={w} ep={ep} ({t0})",
            flush=True,
        )
        try:
            wape, best_ep = run_one_config(kind, h, lay, lr, w, ep)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            _append_row(
                out,
                f"{kind},{h},{lay},{lr},{w},{ep},FAIL,0,{datetime.datetime.now().isoformat()},0",
            )
            continue

        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if wape != wape:  # NaN check
            print("  -> TIMEOUT or FAIL", flush=True)
            _append_row(out, f"{kind},{h},{lay},{lr},{w},{ep},TIMEOUT,0,{date},0")
        else:
            print(f"  -> wape_score={wape:.4f}", flush=True)
            _append_row(
                out, f"{kind},{h},{lay},{lr},{w},{ep},{wape:.4f},{best_ep},{date},1"
            )

    print(f"sweep done -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
