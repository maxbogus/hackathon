"""Predictions CSV + submission manifest parsing (T-230).

Единый источник правды для формата submission-артефактов (clinerule 23):
    route;date;hour;prediction        ← header есть, separator ";"

Нужно, чтобы:
  - `app/scripts/seed_predictions.py` сеял эталон из `data/real/test_submission.csv`;
  - `app/predictions_active.py` ingest'ил кандидата, который сгенерировал
    Celery-worker в shared volume `predictions/`.

Модуль намеренно не логирует и не конфигурирует logging (в отличие от
seed-скрипта) — его импортирует runtime API.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

__all__ = [
    "find_manifest_for_submission",
    "load_predictions_csv",
    "read_manifest",
]


def load_predictions_csv(csv_path: Path) -> list[dict[str, Any]]:
    """Читает submission CSV → список dict с полями для INSERT.

    Ожидаемый формат: `route;date;hour;prediction` (header обязателен,
    separator `;`). Битrowые/неполные строки молча пропускаются.

    Returns:
        list[dict] с ключами: route_id, period_start, period_end, value.
    """
    rows: list[dict[str, Any]] = []
    if not csv_path.exists():
        return rows

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            parsed = _parse_row(row)
            if parsed is not None:
                rows.append(parsed)
    return rows


def _parse_row(row: dict[str, str | None]) -> dict[str, Any] | None:
    """Одна строка CSV → dict, либо None если строка мусорная."""
    route_id = _to_int(row.get("route"))
    hour = _to_int(row.get("hour"))
    date_raw = (row.get("date") or "").strip()
    value = _to_float(row.get("prediction"))
    if route_id is None or hour is None or not date_raw or value is None:
        return None
    try:
        date = datetime.fromisoformat(date_raw)
    except ValueError:
        return None

    period_start = date.replace(hour=hour, minute=0, second=0, microsecond=0)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=UTC)
    return {
        "route_id": route_id,
        "period_start": period_start,
        "period_end": period_start + timedelta(hours=1),
        "value": float(value),
    }


def _to_int(raw: object) -> int | None:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _to_float(raw: object) -> float | None:
    try:
        return float(str(raw).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def read_manifest(manifest_path: Path) -> dict[str, Any] | None:
    """Читает submission manifest.json; None если файла нет или он битый."""
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def find_manifest_for_submission(
    predictions_dir: Path, submission_id: str
) -> Path | None:
    """Ищет самый новый manifest с данным submission_id.

    Устойчивее, чем парсинг stdout Celery-задачи (clinerule 24: artefakt
    на диске = source of truth).

    Returns:
        Path к .json или None.
    """
    best: tuple[float, Path] | None = None
    for path in predictions_dir.glob("*.json"):
        manifest = read_manifest(path)
        if manifest is None or manifest.get("submission_id") != submission_id:
            continue
        mtime = path.stat().st_mtime
        if best is None or mtime > best[0]:
            best = (mtime, path)
    return best[1] if best else None
