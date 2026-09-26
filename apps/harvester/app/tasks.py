"""Celery tasks для harvester.

В режиме `local` (по умолчанию):
    Читает существующие data/external/*.json и нормализует в формат,
    совместимый с downstream ML-фичами (weather_openmeteo.py, traffic_osm.py,
    poi_features.py).

В режиме `online` (HARVESTER_MODE=online):
    Ходит в реальные API (Open-Meteo, OSM Overpass) и пишет JSON.

Все таски возвращают dict с метаданными:
    {"source": str, "rows": int, "output_path": str, "ts": iso8601}
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from celery import shared_task
import httpx

from app.config import settings


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _save_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def _load_json_or_empty(path: Path) -> dict | list:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


# ─────────────────────────── Weather ───────────────────────────────────


@shared_task(name="harvester.fetch_weather_json", bind=True, max_retries=2)
def fetch_weather_json(
    self,
    lat: float = 55.75,
    lon: float = 37.62,
    start_date: str = "2025-01-01",
    end_date: str = "2025-12-31",
) -> dict:
    """Fetch weather JSON for Moscow bbox.

    local mode: returns data/external/weather_2025.csv summary as JSON.
    online mode: GET Open-Meteo archive API.
    """
    if settings.mode == "local":
        # R4 hackathon-rules safe: read pre-fetched CSV/JSON, normalise.
        src = settings.external_dir / "weather_2025.csv"
        if not src.exists():
            return {
                "source": "weather", "rows": 0, "output_path": "", "ts": _now_iso(),
                "warning": f"missing {src}",
            }
        rows: list[dict] = []
        for line in src.read_text().splitlines()[1:]:  # skip header
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                rows.append({"date": parts[0], "temp_c": parts[1], "precip": parts[2]})
        out_path = settings.external_dir / "weather_normalized.json"
        _save_json(out_path, {"source": "weather_openmeteo", "rows": rows})
        return {
            "source": "weather_openmeteo",
            "rows": len(rows),
            "output_path": str(out_path),
            "ts": _now_iso(),
        }

    # online mode
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "Europe/Moscow",
    }
    with httpx.Client(timeout=settings.http_timeout_sec) as client:
        resp = client.get(settings.openmeteo_url, params=params)
        resp.raise_for_status()
        payload = resp.json()
    out_path = settings.external_dir / f"weather_{start_date}_{end_date}.json"
    _save_json(out_path, payload)
    return {
        "source": "weather_openmeteo",
        "rows": len(payload.get("daily", {}).get("time", [])),
        "output_path": str(out_path),
        "ts": _now_iso(),
    }


# ─────────────────────────── Traffic (OSM) ────────────────────────────


@shared_task(name="harvester.fetch_traffic_json", bind=True, max_retries=2)
def fetch_traffic_json(self) -> dict:
    """Fetch traffic data for Moscow bbox (hardcoded OSM extract).

    local mode: returns data/external/traffic_osm_moscow.json.
    online mode: Overpass API query.
    """
    if settings.mode == "local":
        src = settings.external_dir / "traffic_osm_moscow.json"
        payload = _load_json_or_empty(src)
        out_path = settings.external_dir / "traffic_normalized.json"
        if isinstance(payload, dict):
            # Поддержка разных схем: elements (Overpass) / _points (T-124)
            rows = payload.get("elements") or payload.get("_points") or []
        else:
            rows = payload
        _save_json(out_path, {"source": "traffic_osm", "rows": rows})
        return {
            "source": "traffic_osm",
            "rows": len(rows) if isinstance(rows, list) else 0,
            "output_path": str(out_path),
            "ts": _now_iso(),
        }

    query = (
        '[out:json][timeout:60];'
        '(way["highway"~"primary|secondary|tertiary"](55.5,37.3,55.9,37.9););'
        'out tags;'
    )
    with httpx.Client(timeout=settings.http_timeout_sec) as client:
        resp = client.post(settings.overpass_url, data={"data": query})
        resp.raise_for_status()
        payload = resp.json()
    out_path = settings.external_dir / "traffic_osm_moscow.json"
    _save_json(out_path, payload)
    return {
        "source": "traffic_osm",
        "rows": len(payload.get("elements", [])),
        "output_path": str(out_path),
        "ts": _now_iso(),
    }


# ─────────────────────────── POI ───────────────────────────────────────


@shared_task(name="harvester.fetch_poi_json", bind=True, max_retries=2)
def fetch_poi_json(self) -> dict:
    """Fetch POI (points of interest) for Moscow bbox.

    local mode: returns data/external/poi_moscow.json (146 POI, 13 categories).
    """
    src = settings.external_dir / "poi_moscow.json"
    payload = _load_json_or_empty(src)
    out_path = settings.external_dir / "poi_normalized.json"
    rows = payload.get("pois", []) if isinstance(payload, dict) else payload
    if isinstance(rows, list):
        _save_json(out_path, {"source": "poi_osm", "rows": rows})
        return {
            "source": "poi_osm",
            "rows": len(rows),
            "output_path": str(out_path),
            "ts": _now_iso(),
        }
    return {
        "source": "poi_osm", "rows": 0, "output_path": "", "ts": _now_iso(),
        "warning": f"unexpected shape in {src}",
    }


# ─────────────────────────── Events ────────────────────────────────────


@shared_task(name="harvester.fetch_events_json", bind=True, max_retries=2)
def fetch_events_json(self) -> dict:
    """Fetch events calendar (infrastructure openings, holidays, etc.)."""
    src = settings.external_dir / "events_moscow.json"
    payload = _load_json_or_empty(src)
    out_path = settings.external_dir / "events_normalized.json"
    if isinstance(payload, dict):
        # Поддержка разных схем: events / _events (T-172)
        rows = payload.get("events") or payload.get("_events") or []
    else:
        rows = payload
    if isinstance(rows, list):
        _save_json(out_path, {"source": "events_misc", "rows": rows})
        return {
            "source": "events_misc",
            "rows": len(rows),
            "output_path": str(out_path),
            "ts": _now_iso(),
        }
    return {"source": "events_misc", "rows": 0, "output_path": "", "ts": _now_iso()}


# ─────────────────────────── All-in-one ────────────────────────────────


@shared_task(name="harvester.fetch_all", bind=True)
def fetch_all(self) -> dict:
    """Run all fetch tasks sequentially. Returns aggregated metadata."""
    results = {
        "weather": fetch_weather_json(),
        "traffic": fetch_traffic_json(),
        "poi": fetch_poi_json(),
        "events": fetch_events_json(),
    }
    return {"status": "ok", "results": results, "ts": _now_iso()}
