#!/usr/bin/env python3
"""Сверка двух submission-CSV (T-235, Tier A).

Зачем: пилот проверяет, что пайплайн воспроизводит ожидаемый результат. Нужны
машинные числа: детерминизм (sha256), структура (grid 10×61×24), сходство с
эталоном (сколько ключей совпало, max|Δ|, суммы, число нулей).

Usage:
    uv run python scripts/compare_submissions.py --left predictions/a.csv --right predictions/b.csv
    uv run python scripts/compare_submissions.py --left a.csv --right b.csv --json reports/compare.json

Exit code:
    0 — отчёт построен (расхождение допустимо, оно описывается числами);
    2 — структурная ошибка (не тот grid/формат), т.е. воспроизведение не удалось.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

EXPECTED_ROWS = 10 * 61 * 24  # 10 маршрутов × 61 день × 24 часа = 14640 (F-045)
EXPECTED_COLUMNS = ["route", "date", "hour", "prediction"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> pd.DataFrame:
    """Прочитать submission CSV (separator=';', float/int prediction)."""
    frame = pd.read_csv(path, sep=";")
    missing = [c for c in EXPECTED_COLUMNS if c not in frame.columns]
    if missing:
        raise SystemExit(f"{path}: нет колонок {missing}; есть {list(frame.columns)}")
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    frame["prediction"] = frame["prediction"].astype(float)
    return frame


def describe(path: Path) -> dict:
    """Структурный отчёт по одному файлу."""
    frame = _read(path)
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "rows": len(frame),
        "rows_ok": len(frame) == EXPECTED_ROWS,
        "routes": sorted(int(r) for r in frame["route"].unique()),
        "days": int(frame["date"].nunique()),
        "hours": sorted(int(h) for h in frame["hour"].unique()),
        "zeros": int((frame["prediction"] == 0).sum()),
        "sum": float(frame["prediction"].sum()),
        "negatives": int((frame["prediction"] < 0).sum()),
    }


def compare(left_path: Path, right_path: Path) -> dict:
    """Сравнить два submission: структура + по-ключевое расхождение."""
    left = _read(left_path)
    right = _read(right_path)
    keys = ["route", "date", "hour"]

    merged = left.merge(right, on=keys, how="outer", suffixes=("_left", "_right"), indicator=True)
    both = merged[merged["_merge"] == "both"]
    diff = (both["prediction_left"] - both["prediction_right"]).abs()

    return {
        "left": describe(left_path),
        "right": describe(right_path),
        "same_sha256": describe(left_path)["sha256"] == describe(right_path)["sha256"],
        "keys_left_only": int((merged["_merge"] == "left_only").sum()),
        "keys_right_only": int((merged["_merge"] == "right_only").sum()),
        "keys_both": len(both),
        "keys_differing": int((diff > 1e-9).sum()),
        "max_abs_delta": float(diff.max()) if len(diff) else 0.0,
        "mean_abs_delta": float(diff.mean()) if len(diff) else 0.0,
        "sum_delta": float(left["prediction"].sum() - right["prediction"].sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Сверка двух submission CSV (T-235)")
    parser.add_argument(
        "--left", required=True, type=Path, help="первый CSV (например, новый прогон)"
    )
    parser.add_argument("--right", required=True, type=Path, help="второй CSV (эталон)")
    parser.add_argument("--json", type=Path, default=None, help="куда сохранить JSON-отчёт")
    args = parser.parse_args()

    report = compare(args.left, args.right)

    print(
        f"left  : {report['left']['path']} sha256={report['left']['sha256'][:16]} rows={report['left']['rows']}"
    )
    print(
        f"right : {report['right']['path']} sha256={report['right']['sha256'][:16]} rows={report['right']['rows']}"
    )
    print(f"identical bytes        : {report['same_sha256']}")
    print(f"structure ok           : {report['left']['rows_ok'] and report['right']['rows_ok']}")
    print(f"routes                 : {report['left']['routes']} vs {report['right']['routes']}")
    print(f"zeros                  : {report['left']['zeros']} vs {report['right']['zeros']}")
    print(
        f"sum                    : {report['left']['sum']:.2f} vs {report['right']['sum']:.2f} (Δ {report['sum_delta']:.2f})"
    )
    print(f"keys left/right only   : {report['keys_left_only']} / {report['keys_right_only']}")
    print(f"keys differing         : {report['keys_differing']} из {report['keys_both']}")
    print(
        f"max|Δ| / mean|Δ|       : {report['max_abs_delta']:.4f} / {report['mean_abs_delta']:.4f}"
    )
    print(f"negatives              : {report['left']['negatives']} (должно быть 0)")

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON: {args.json}")

    structural_ok = (
        report["left"]["rows_ok"]
        and report["right"]["rows_ok"]
        and report["left"]["negatives"] == 0
        and report["keys_left_only"] == 0
        and report["keys_right_only"] == 0
    )
    return 0 if structural_ok else 2


if __name__ == "__main__":
    sys.exit(main())
