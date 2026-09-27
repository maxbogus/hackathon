"""External ETL builders (шаг 0, T-231).

Каждый builder — чистая функция: читает raw-файл под `repo_root` и пишет
нормализованный артефакт в `out_dir`. Формат артефакта совпадает с тем, что
уже писали Celery-таски (`{"source", "rows"}`), и дополнен метаданными
(`rows_count`, `generated_at`, `inputs`) для `manifest.json`.

R4 hackathon-rules: только локальные файлы, никаких сетевых вызовов.
Детерминизм: `generated_at` берётся из `SOURCE_DATE_EPOCH` или mtime входов,
поэтому два прогона дают побайтово одинаковый артефакт.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT

# ─────────────────────────── конфигурация ──────────────────────────────

RAW_SOURCES: dict[str, str] = {
    "weather": "data/external/weather_2025.csv",
    "traffic": "data/external/traffic_osm_moscow.json",
    "poi": "data/external/poi_moscow.json",
    "events": "data/external/events_moscow.json",
    "stops": "data/external/stops_routes.json",
    "validators": "data/external/validators_lookup.csv",
    "holidays": "data/external/holidays_ru_2025.json",
    "school_breaks": "data/external/school_breaks_2025.json",
    "user_routes": "ml/transit_ai/data/_user_routes_2025.json",
}

OUT_FILES: dict[str, str] = {
    "weather": "weather.json",
    "traffic": "traffic.json",
    "poi": "poi.json",
    "events": "events.json",
    "stops": "stops.json",
    "validators": "validators.json",
    "calendar": "calendar.json",
    "user_routes": "user_routes.json",
}

SOURCES: tuple[str, ...] = tuple(OUT_FILES)

DEFAULT_OUT_SUBDIR = Path("data") / "external" / "normalized"

WEATHER_COLUMNS = (
    "temp_max",
    "temp_min",
    "precipitation_sum",
    "snowfall_sum",
    "wind_speed_max",
)

VALIDATORS_COLUMNS = ("route_id", "weekday", "hour", "n_validators_mean", "n_trams_mean")


# ─────────────────────────── утилиты ───────────────────────────────────


def sha256_bytes(data: bytes) -> str:
    """sha256 от байтов (hex, 64 символа)."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """sha256 от файла (hex, 64 символа)."""
    return sha256_bytes(path.read_bytes())


def now_iso() -> str:
    """Текущее UTC-время в ISO-8601 (секунды) — как в app.tasks._now_iso."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def generated_at(inputs: list[Path], source_epoch: str | None = None) -> str:
    """Детерминированная метка сборки.

    Приоритет: явный `source_epoch` → `SOURCE_DATE_EPOCH` → максимальный mtime
    входов. Никакого `now()`, иначе хэши артефактов «плывут» между прогонами.
    """
    if source_epoch:
        return source_epoch
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return datetime.fromtimestamp(int(epoch), tz=UTC).isoformat(timespec="seconds")
    mtimes = [p.stat().st_mtime for p in inputs if p.exists()]
    if not mtimes:
        return "1970-01-01T00:00:00+00:00"
    return datetime.fromtimestamp(max(mtimes), tz=UTC).isoformat(timespec="seconds")


def resolve_paths(repo_root: Path | str | None, out_dir: Path | str | None) -> tuple[Path, Path]:
    """(repo_root, out_dir) с дефолтами: корень репо и `data/external/normalized`."""
    root = Path(repo_root) if repo_root else REPO_ROOT
    out = Path(out_dir) if out_dir else root / DEFAULT_OUT_SUBDIR
    return root, out


def raw_path(repo_root: Path, key: str) -> Path:
    """Путь к raw-источнику (относительно repo_root)."""
    return repo_root / RAW_SOURCES[key]


def _as_float(value: object, default: float = 0.0) -> float:
    """float из строки/числа; пустое/битое — default."""
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return default


def _as_int(value: object, default: int = 0) -> int:
    """int из строки/числа (сначала как int, потом как float)."""
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        return int(_as_float(text, float(default)))


def load_json(path: Path) -> Any:
    """Прочитать JSON (UTF-8)."""
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────── результат сборки ──────────────────────────


@dataclass(frozen=True)
class BuildResult:
    """Результат сборки одного источника."""

    source: str
    rows_count: int
    output_path: Path
    payload: dict[str, Any]
    inputs: tuple[dict[str, Any], ...]
    output_sha256: str
    generated_at: str
    warning: str | None = None

    def to_task_dict(self) -> dict[str, Any]:
        """Формат Celery-тасков: source/rows/output_path/ts (+ warning)."""
        out: dict[str, Any] = {
            "source": self.source,
            "rows": self.rows_count,
            "output_path": str(self.output_path),
            "ts": self.generated_at,
        }
        if self.warning:
            out["warning"] = self.warning
        return out


def write_artifact(
    source: str,
    out_dir: Path,
    body: dict[str, Any],
    rows_count: int,
    inputs: list[tuple[Path, int]],
    source_epoch: str | None = None,
    warning: str | None = None,
) -> BuildResult:
    """Записать нормализованный артефакт `<out_dir>/<OUT_FILES[source]>`.

    `body` — специфичные для источника данные (обычно `{"rows": [...]}`).
    Метаданные (`source`, `rows_count`, `generated_at`, `inputs`) добавляются здесь.
    """
    present = [p for p, _ in inputs if p.exists()]
    payload: dict[str, Any] = {
        "source": source,
        **body,
        "rows_count": rows_count,
        "generated_at": generated_at(present, source_epoch),
        "inputs": [
            {"path": str(p), "sha256": sha256_file(p), "rows": n} for p, n in inputs if p.exists()
        ],
    }
    out_path = out_dir / OUT_FILES[source]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    out_path.write_text(text, encoding="utf-8")
    return BuildResult(
        source=source,
        rows_count=rows_count,
        output_path=out_path,
        payload=payload,
        inputs=tuple(payload["inputs"]),
        output_sha256=sha256_bytes(text.encode("utf-8")),
        generated_at=payload["generated_at"],
        warning=warning,
    )


# ─────────────────────────── builders ──────────────────────────────────


def build_weather(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """Погода: CSV → JSON со всеми 6 колонками, числовые — float."""
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "weather")
    if not src.exists():
        return write_artifact("weather", out, {"rows": []}, 0, [], source_epoch, f"missing {src}")
    rows: list[dict[str, Any]] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw_row in csv.DictReader(fh):
            row: dict[str, Any] = {"date": str(raw_row.get("date", ""))}
            for column in WEATHER_COLUMNS:
                row[column] = _as_float(raw_row.get(column))
            rows.append(row)
    return write_artifact(
        "weather", out, {"rows": rows}, len(rows), [(src, len(rows))], source_epoch
    )


def build_traffic(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """Трафик: `_points` → `rows` (поля id/lat/lon/category/jam_level/notes)."""
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "traffic")
    if not src.exists():
        return write_artifact("traffic", out, {"rows": []}, 0, [], source_epoch, f"missing {src}")
    payload = load_json(src)
    raw_rows = payload.get("_points", []) if isinstance(payload, dict) else payload
    rows = [r for r in raw_rows if isinstance(r, dict)]
    return write_artifact(
        "traffic", out, {"rows": rows}, len(rows), [(src, len(rows))], source_epoch
    )


def build_poi(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """POI: список объектов `[{name, category, lat, lon}]` → `rows`."""
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "poi")
    if not src.exists():
        return write_artifact("poi", out, {"rows": []}, 0, [], source_epoch, f"missing {src}")
    payload = load_json(src)
    raw_rows = payload.get("pois", []) if isinstance(payload, dict) else payload
    rows = [r for r in raw_rows if isinstance(r, dict)]
    return write_artifact("poi", out, {"rows": rows}, len(rows), [(src, len(rows))], source_epoch)


def build_events(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """События: схемы `_events` (актуальная) и `events` → `rows`."""
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "events")
    if not src.exists():
        return write_artifact("events", out, {"rows": []}, 0, [], source_epoch, f"missing {src}")
    payload = load_json(src)
    if isinstance(payload, dict):
        raw_rows = payload.get("_events") or payload.get("events") or []
    else:
        raw_rows = payload
    rows = [r for r in raw_rows if isinstance(r, dict)]
    return write_artifact(
        "events", out, {"rows": rows}, len(rows), [(src, len(rows))], source_epoch
    )


def build_stops(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """Остановки: `{route_id: [stops]}` → `{"routes": {...}}` (без `_comment`)."""
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "stops")
    if not src.exists():
        return write_artifact("stops", out, {"routes": {}}, 0, [], source_epoch, f"missing {src}")
    payload = load_json(src)
    routes: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.startswith("_") or not isinstance(value, list):
                continue
            routes[str(key)] = value
    rows_count = sum(len(stops) for stops in routes.values())
    return write_artifact(
        "stops", out, {"routes": routes}, rows_count, [(src, rows_count)], source_epoch
    )


def build_validators(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """Валидаторы: CSV-кэш → JSON.

    `data/real/train.csv` (9.7 ГБ) здесь НЕ читается: агрегация делается
    ML-модулем `transit_ai.data.validators_lookup` (pandas), а ETL только
    нормализует готовый CSV-кэш.
    """
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "validators")
    if not src.exists():
        return write_artifact(
            "validators",
            out,
            {"rows": []},
            0,
            [],
            source_epoch,
            f"missing {src} (build it via transit_ai.data.validators_lookup)",
        )
    rows: list[dict[str, Any]] = []
    with src.open(encoding="utf-8", newline="") as fh:
        for raw_row in csv.DictReader(fh):
            rows.append(
                {
                    "route_id": _as_int(raw_row.get("route_id")),
                    "weekday": _as_int(raw_row.get("weekday")),
                    "hour": _as_int(raw_row.get("hour")),
                    "n_validators_mean": _as_float(raw_row.get("n_validators_mean")),
                    "n_trams_mean": _as_float(raw_row.get("n_trams_mean")),
                }
            )
    return write_artifact(
        "validators", out, {"rows": rows}, len(rows), [(src, len(rows))], source_epoch
    )


def build_calendar(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """Календарь: праздники РФ + школьные каникулы в один артефакт."""
    root, out = resolve_paths(repo_root, out_dir)
    holidays_src = raw_path(root, "holidays")
    breaks_src = raw_path(root, "school_breaks")
    holidays: list[str] = []
    school_breaks: list[list[str]] = []
    if holidays_src.exists():
        payload = load_json(holidays_src)
        holidays = [str(item) for item in payload.get("holidays", [])]
    if breaks_src.exists():
        payload = load_json(breaks_src)
        school_breaks = [[str(item[0]), str(item[1])] for item in payload.get("school_breaks", [])]
    rows_count = len(holidays) + len(school_breaks)
    return write_artifact(
        "calendar",
        out,
        {"holidays": holidays, "school_breaks": school_breaks},
        rows_count,
        [(holidays_src, len(holidays)), (breaks_src, len(school_breaks))],
        source_epoch,
    )


def build_user_routes(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    source_epoch: str | None = None,
) -> BuildResult:
    """User-разметка маршрутов (17/25/26/28/50) → `{"routes": {...}}`."""
    root, out = resolve_paths(repo_root, out_dir)
    src = raw_path(root, "user_routes")
    if not src.exists():
        return write_artifact(
            "user_routes", out, {"routes": {}}, 0, [], source_epoch, f"missing {src}"
        )
    payload = load_json(src)
    routes: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.startswith("_"):
                continue
            routes[str(key)] = value
    return write_artifact(
        "user_routes", out, {"routes": routes}, len(routes), [(src, len(routes))], source_epoch
    )


BUILDERS: dict[str, Any] = {
    "weather": build_weather,
    "traffic": build_traffic,
    "poi": build_poi,
    "events": build_events,
    "stops": build_stops,
    "validators": build_validators,
    "calendar": build_calendar,
    "user_routes": build_user_routes,
}
