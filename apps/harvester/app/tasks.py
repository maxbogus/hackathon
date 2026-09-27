"""Celery tasks harvester (T-193; ETL делегирован в `app.build` — T-231).

`local` (default): нормализация локальных raw-файлов через `app.build.builders`
→ `data/external/normalized/*.json`; `fetch_all` дополнительно пишет `manifest.json`.
`online` (`HARVESTER_MODE=online`, dev only): скачать raw из Open-Meteo / Overpass.

Возвращаемый формат (как `BuildResult.to_task_dict()`):
    {"source": str, "rows": int, "output_path": str, "ts": iso8601}
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from celery import shared_task
import httpx

from app.build import builders as build, pipeline
from app.config import settings


def _now_iso() -> str:
    """Текущее UTC-время в ISO-8601 (секунды)."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _save_json(path: Path, payload: dict | list) -> Path:
    """Записать JSON (UTF-8, отступ 2) — для online-дампов."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def _repo_root() -> Path:
    """Корень репозитория (в контейнере /app, локально — корень hackathon/)."""
    return settings.data_dir.parent


def _out_dir() -> Path:
    """Куда писать нормализованные артефакты."""
    return settings.external_dir / "normalized"


def _local(name: str) -> dict:
    """Local-режим: нормализовать raw → `normalized/<name>.json`."""
    result = build.BUILDERS[name](repo_root=_repo_root(), out_dir=_out_dir())
    return result.to_task_dict()


# ─────────────────────────── Weather ───────────────────────────────────


@shared_task(name="harvester.fetch_weather_json", bind=True, max_retries=2)
def fetch_weather_json(
    self,
    lat: float = 55.75,
    lon: float = 37.62,
    start_date: str = "2025-01-01",
    end_date: str = "2025-12-31",
) -> dict:
    """Погода: local → normalized/weather.json; online → raw-дамп Open-Meteo."""
    if settings.mode != "online":
        return _local("weather")

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
    out_path = _save_json(settings.external_dir / f"weather_{start_date}_{end_date}.json", payload)
    return {
        "source": "weather_openmeteo",
        "rows": len(payload.get("daily", {}).get("time", [])),
        "output_path": str(out_path),
        "ts": _now_iso(),
    }


# ─────────────────────────── Traffic ───────────────────────────────────


@shared_task(name="harvester.fetch_traffic_json", bind=True, max_retries=2)
def fetch_traffic_json(self) -> dict:
    """Трафик: local → normalized/traffic.json; online → raw-дамп Overpass (dev)."""
    if settings.mode != "online":
        return _local("traffic")

    query = (
        "[out:json][timeout:60];"
        '(way["highway"~"primary|secondary|tertiary"](55.5,37.3,55.9,37.9););'
        "out tags;"
    )
    with httpx.Client(timeout=settings.http_timeout_sec) as client:
        resp = client.post(settings.overpass_url, data={"data": query})
        resp.raise_for_status()
        payload = resp.json()
    out_path = _save_json(settings.external_dir / "traffic_osm_online.json", payload)
    return {
        "source": "traffic_osm",
        "rows": len(payload.get("elements", [])),
        "output_path": str(out_path),
        "ts": _now_iso(),
    }


# ─────────────────────────── POI ───────────────────────────────────────


@shared_task(name="harvester.fetch_poi_json", bind=True, max_retries=2)
def fetch_poi_json(self) -> dict:
    """POI: local → normalized/poi.json; online → raw-дамп Overpass (dev)."""
    if settings.mode != "online":
        return _local("poi")

    query = (
        "[out:json][timeout:60];"
        '(node["amenity"~"school|university|hospital"](55.5,37.3,55.9,37.9);'
        'way["leisure"="park"](55.5,37.3,55.9,37.9););'
        "out center tags;"
    )
    with httpx.Client(timeout=settings.http_timeout_sec) as client:
        resp = client.post(settings.overpass_url, data={"data": query})
        resp.raise_for_status()
        payload = resp.json()
    out_path = _save_json(settings.external_dir / "poi_osm_online.json", payload)
    return {
        "source": "poi_osm",
        "rows": len(payload.get("elements", [])),
        "output_path": str(out_path),
        "ts": _now_iso(),
    }


# ─────────────────────────── Events ────────────────────────────────────


@shared_task(name="harvester.fetch_events_json", bind=True, max_retries=2)
def fetch_events_json(self) -> dict:
    """События: только локальный каталог (R4) → normalized/events.json."""
    return _local("events")


# ─────────────────────────── All-in-one ────────────────────────────────


@shared_task(name="harvester.fetch_all", bind=True)
def fetch_all(self) -> dict:
    """Собрать все источники → normalized/*.json + manifest.json."""
    if settings.mode == "online":
        for task in (fetch_weather_json, fetch_traffic_json, fetch_poi_json):
            task()
    summary = pipeline.build_all(repo_root=_repo_root(), out_dir=_out_dir(), mode=settings.mode)
    return {
        "status": "ok",
        "results": {name: meta["rows_count"] for name, meta in summary["sources"].items()},
        "manifest": summary["manifest_path"],
        "ts": _now_iso(),
    }
