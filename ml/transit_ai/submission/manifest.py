"""submission_manifest.json writer/validator (T-148a, F-021, clinerule 23).

Каждый submission на платформу хакатона = атомарный артефакт:
    <csv_basename>.csv
    <csv_basename>.json   ← этот модуль (manifest)

Имя CSV по R1: submission_<model_id>_<start_date>_<end_date>_<run_ts>.csv
Обязательные поля по R2: см. write_manifest() docstring.
Verify по R4: см. verify_manifest() docstring.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

__all__ = [
    "dataset_hash",
    "git_branch",
    "git_commit",
    "verify_manifest",
    "write_manifest",
]


def git_commit() -> str:
    """Короткий git commit hash текущего HEAD (R3 reproducible)."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def git_branch() -> str:
    """Имя текущей ветки (для traceability)."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def dataset_hash(paths: list[Path]) -> str:
    """sha256 от сортированного списка файлов (R3 reproducible)."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def write_manifest(
    out_dir: Path,
    csv_filename: str,
    model_id: str,
    model_uri: str,
    train_range: tuple[str, str],
    sub_range: tuple[str, str],
    row_count: int,
    expected_rows: int,
    total_predictions: float,
    coefficients: dict[str, float],
    post_processing: list[str],
    holdout_wape_score: float | None = None,
    submission_id: str | None = None,
    dataset_hash_sha256: str | None = None,
) -> Path:
    """Записать submission_manifest.json рядом с CSV.

    Args:
        out_dir: директория для записи (например predictions/).
        csv_filename: имя CSV файла (должно соответствовать R1 clinerule 23).
        model_id: идентификатор модели из ml/artifacts/<model_id>/meta.json.
        model_uri: относительный путь к model.pkl (или .pt/.onnx).
        train_range: (start_iso_date, end_iso_date) тренировочной выборки.
        sub_range: (start_iso_date, end_iso_date) прогнозного периода.
        row_count: реальное количество строк в CSV.
        expected_rows: ожидаемое количество строк (для detect drift).
        total_predictions: сумма predictions (sanity check).
        coefficients: dict корректирующих коэффициентов (T-147).
        post_processing: список применённых пост-обработок.
        holdout_wape_score: WAPE-score на holdout (опционально).
        submission_id: человеко-читаемый id (R5). Default = model_id.
        dataset_hash_sha256: sha256 от parquet (если None — "unknown").

    Returns:
        Path к записанному .json файлу.
    """
    if submission_id is None:
        submission_id = model_id

    manifest: dict[str, Any] = {
        "submission_id": submission_id,
        "csv_filename": csv_filename,
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "git_branch": git_branch(),
        "data_source": "RealSource",
        "dataset_hash_sha256": dataset_hash_sha256 or "unknown",
        "model_id": model_id,
        "model_uri": model_uri,
        "train_date_range": list(train_range),
        "submission_date_range": list(sub_range),
        "row_count": row_count,
        "expected_rows": expected_rows,
        "total_predictions_sum": float(total_predictions),
        "coefficients": dict(coefficients),
        "post_processing": list(post_processing),
        "platform_submitted": False,
        "platform_score": None,
        "platform_score_submitted_at": None,
        "holdout_wape_score": holdout_wape_score,
    }

    out = Path(out_dir) / csv_filename.replace(".csv", ".json")
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return out


def verify_manifest(manifest_path: Path, csv_path: Path) -> int:
    """Проверить что manifest соответствует CSV (R4 clinerule 23).

    Args:
        manifest_path: путь к submission_manifest.json.
        csv_path: путь к проверяемому submission_*.csv.

    Returns:
        0 если всё ОК, non-zero (1) если есть mismatch.

    Проверки:
        1. manifest_path существует
        2. csv_path существует
        3. manifest.csv_filename == csv_path.name
        4. manifest.row_count == реальное число строк в CSV (без header)
        5. manifest.expected_rows == manifest.row_count (drift detect)
    """
    if not manifest_path.exists():
        print(f"[FAIL] manifest not found: {manifest_path}")
        return 1
    if not csv_path.exists():
        print(f"[FAIL] csv not found: {csv_path}")
        return 1

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"[FAIL] manifest is not valid JSON: {e}")
        return 1

    declared_csv = manifest.get("csv_filename")
    if declared_csv != csv_path.name:
        print(
            f"[FAIL] manifest.csv_filename={declared_csv!r} != csv name={csv_path.name!r}"
        )
        return 1

    # Считаем реальные строки (без header)
    with csv_path.open() as f:
        actual_rows = sum(1 for _ in f) - 1
    declared_rows = manifest.get("row_count")
    if declared_rows != actual_rows:
        print(
            f"[FAIL] manifest.row_count={declared_rows} != actual CSV rows={actual_rows}"
        )
        return 1

    expected_rows = manifest.get("expected_rows")
    if expected_rows != declared_rows:
        print(
            f"[FAIL] manifest.expected_rows={expected_rows} != row_count={declared_rows}"
        )
        return 1

    print(
        f"[OK] manifest verified: {csv_path.name} ({actual_rows} rows, model={manifest.get('model_id')})"
    )
    return 0
