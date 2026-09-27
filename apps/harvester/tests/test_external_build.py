"""RED-тесты external ETL (шаг 0, T-231).

Проверяют `app.build` — детерминированный пайплайн «внешние источники → JSON
для обучения». Формат normalized совпадает с тем, что уже пишут Celery-таски
(`{"source", "rows"}`) плюс метаданные: `rows_count`, `generated_at`, `inputs`.

Запуск:
    cd apps/harvester && uv run pytest tests/test_external_build.py -v --no-cov
"""

from __future__ import annotations

import json
from pathlib import Path

from app.build import builders, pipeline
from app.build.cli import main as cli_main
import pytest

WEATHER_CSV = (
    "date,temp_max,temp_min,precipitation_sum,snowfall_sum,wind_speed_max\n"
    "2025-01-01,1.3,-6.8,3.9,2.66,19.8\n"
    "2025-01-02,3.1,1.3,2.0,0.07,26.8\n"
)

EXPECTED_SOURCES = {
    "weather",
    "traffic",
    "poi",
    "events",
    "stops",
    "validators",
    "calendar",
    "user_routes",
}


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Мини-репозиторий с raw-файлами (форматы 1:1 как в data/external/)."""
    ext = tmp_path / "data" / "external"
    ext.mkdir(parents=True)
    (ext / "weather_2025.csv").write_text(WEATHER_CSV, encoding="utf-8")
    (ext / "traffic_osm_moscow.json").write_text(
        json.dumps(
            {
                "_points": [
                    {
                        "id": "t1",
                        "lat": 55.75,
                        "lon": 37.61,
                        "category": "major_arterial",
                        "jam_level": 4,
                        "notes": "Тверская",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ext / "poi_moscow.json").write_text(
        json.dumps(
            [{"name": "МГУ", "category": "university", "lat": 55.7038, "lon": 37.5306}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ext / "events_moscow.json").write_text(
        json.dumps(
            {
                "_comment": "c",
                "_events": [
                    {
                        "id": "e1",
                        "date": "2025-09-13",
                        "category": "metro_open",
                        "magnitude": 1.1,
                        "tau_days": 60,
                        "affected_routes": [],
                        "notes": "n",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ext / "stops_routes.json").write_text(
        json.dumps(
            {"_comment": "c", "1": [{"name": "Чертаново", "lat": 55.60112, "lon": 37.585266}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (ext / "validators_lookup.csv").write_text(
        "route_id,weekday,hour,n_validators_mean,n_trams_mean\n1,0,0,2.0,1.0\n",
        encoding="utf-8",
    )
    (ext / "holidays_ru_2025.json").write_text(
        json.dumps({"holidays": ["2025-01-01", "2025-11-04"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (ext / "school_breaks_2025.json").write_text(
        json.dumps({"school_breaks": [["2025-10-27", "2025-11-04"]]}, ensure_ascii=False),
        encoding="utf-8",
    )
    ml_data = tmp_path / "ml" / "transit_ai" / "data"
    ml_data.mkdir(parents=True)
    (ml_data / "_user_routes_2025.json").write_text(
        json.dumps({"_comment": "c", "17": {"n_stops": 52, "name": "Останкино — Медведково"}}),
        encoding="utf-8",
    )
    return tmp_path


def _out_dir(repo: Path) -> Path:
    return repo / "data" / "external" / "normalized"


def _read(out_dir: Path, name: str) -> dict:
    return json.loads((out_dir / name).read_text(encoding="utf-8"))


# ─────────────────────────── builders ──────────────────────────────────


def test_build_weather_preserves_all_csv_columns(fake_repo: Path) -> None:
    """Погода: в normalized сохраняются ВСЕ 6 колонок CSV (не только 3)."""
    res = builders.build_weather(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    assert res.source == "weather"
    assert res.rows_count == 2
    payload = _read(_out_dir(fake_repo), "weather.json")
    assert payload["rows"][0] == {
        "date": "2025-01-01",
        "temp_max": 1.3,
        "temp_min": -6.8,
        "precipitation_sum": 3.9,
        "snowfall_sum": 2.66,
        "wind_speed_max": 19.8,
    }


def test_build_traffic_preserves_required_fields(fake_repo: Path) -> None:
    """Трафик: сохраняются поля, которые требует load_traffic_catalog()."""
    builders.build_traffic(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    rows = _read(_out_dir(fake_repo), "traffic.json")["rows"]
    assert len(rows) == 1
    assert {"id", "lat", "lon", "category", "jam_level", "notes"} <= set(rows[0])


def test_build_poi_passthrough_rows(fake_repo: Path) -> None:
    """POI: список объектов переносится без потерь."""
    res = builders.build_poi(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    assert res.rows_count == 1
    assert _read(_out_dir(fake_repo), "poi.json")["rows"][0]["name"] == "МГУ"


def test_build_events_supports_underscore_events(fake_repo: Path) -> None:
    """События: читается схема `_events` (как в events_moscow.json)."""
    res = builders.build_events(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    assert res.rows_count == 1
    assert _read(_out_dir(fake_repo), "events.json")["rows"][0]["id"] == "e1"


def test_build_stops_keeps_route_mapping(fake_repo: Path) -> None:
    """Остановки: сохраняется маппинг route_id → остановки, `_comment` отброшен."""
    res = builders.build_stops(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    payload = _read(_out_dir(fake_repo), "stops.json")
    assert res.rows_count == 1
    assert payload["routes"]["1"][0]["name"] == "Чертаново"
    assert "_comment" not in payload["routes"]


def test_build_validators_from_csv_cache(fake_repo: Path) -> None:
    """Валидаторы: нормализуется существующий CSV-кэш (train.csv не трогаем)."""
    res = builders.build_validators(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    assert res.rows_count == 1
    row = _read(_out_dir(fake_repo), "validators.json")["rows"][0]
    assert row == {
        "route_id": 1,
        "weekday": 0,
        "hour": 0,
        "n_validators_mean": 2.0,
        "n_trams_mean": 1.0,
    }


def test_build_calendar_shape(fake_repo: Path) -> None:
    """Календарь: праздники + школьные каникулы в одном артефакте."""
    res = builders.build_calendar(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    payload = _read(_out_dir(fake_repo), "calendar.json")
    assert res.rows_count == 3  # 2 праздника + 1 интервал каникул
    assert "2025-11-04" in payload["holidays"]
    assert payload["school_breaks"] == [["2025-10-27", "2025-11-04"]]


def test_build_user_routes_drops_comment(fake_repo: Path) -> None:
    """User-routes: `_comment` отброшен, маршруты сохранены."""
    res = builders.build_user_routes(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    payload = _read(_out_dir(fake_repo), "user_routes.json")
    assert res.rows_count == 1
    assert "_comment" not in payload["routes"]
    assert payload["routes"]["17"]["n_stops"] == 52


def test_build_result_to_task_dict_matches_existing_tasks(fake_repo: Path) -> None:
    """Формат результата совпадает с Celery-тасками: source/rows/output_path/ts."""
    res = builders.build_poi(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    task_dict = res.to_task_dict()
    assert set(task_dict) == {"source", "rows", "output_path", "ts"}
    assert task_dict["source"] == "poi"
    assert task_dict["rows"] == 1
    assert Path(task_dict["output_path"]).exists()


# ─────────────────────────── pipeline ──────────────────────────────────


def test_build_all_writes_manifest_with_all_sources(fake_repo: Path) -> None:
    """manifest.json содержит все 8 источников с sha256 и rows_count."""
    summary = pipeline.build_all(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    sources = summary["sources"]
    assert set(sources) >= EXPECTED_SOURCES
    for name, meta in sources.items():
        assert len(meta["output_sha256"]) == 64, name
        assert meta["rows_count"] >= 0, name
        assert meta["inputs"], name
        assert all(len(i["sha256"]) == 64 for i in meta["inputs"]), name
    manifest = _read(_out_dir(fake_repo), "manifest.json")
    assert manifest["sources"].keys() == sources.keys()


def test_output_hashes_stable_across_two_runs(fake_repo: Path) -> None:
    """Детерминизм: два прогона дают одинаковые output_sha256."""
    first = pipeline.build_all(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    second = pipeline.build_all(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    for name in EXPECTED_SOURCES:
        assert (
            first["sources"][name]["output_sha256"] == second["sources"][name]["output_sha256"]
        ), name


def test_verify_passes_on_fresh_build(fake_repo: Path) -> None:
    pipeline.build_all(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    assert pipeline.verify(out_dir=_out_dir(fake_repo)) == 0


def test_verify_fails_on_truncated_artifact(fake_repo: Path) -> None:
    pipeline.build_all(repo_root=fake_repo, out_dir=_out_dir(fake_repo))
    target = _out_dir(fake_repo) / "poi.json"
    target.write_text(
        '{"source": "poi", "rows": [], "rows_count": 1, "generated_at": "x", "inputs": []}',
        encoding="utf-8",
    )
    assert pipeline.verify(out_dir=_out_dir(fake_repo)) == 1


def test_offline_mode_makes_no_network_calls(
    fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R4: offline-режим не ходит в сеть (любой HTTP-вызов = падение теста)."""

    class _Boom:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("offline mode must not create http clients")

    monkeypatch.setattr("httpx.Client", _Boom)
    summary = pipeline.build_all(repo_root=fake_repo, out_dir=_out_dir(fake_repo), mode="offline")
    assert summary["mode"] == "offline"


# ─────────────────────────── CLI ───────────────────────────────────────


def test_cli_gen_then_verify_exit_codes(fake_repo: Path) -> None:
    """CLI: gen → 0, verify → 0, битый артефакт → 1."""
    out = _out_dir(fake_repo)
    assert cli_main(["--source", "all", "--repo-root", str(fake_repo), "--out", str(out)]) == 0
    assert cli_main(["--verify", "--out", str(out)]) == 0
    (out / "poi.json").write_text("{}", encoding="utf-8")
    assert cli_main(["--verify", "--out", str(out)]) == 1


def test_cli_show_lists_all_sources(fake_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI: --show печатает таблицу по всем источникам с коротким хэшем."""
    out = _out_dir(fake_repo)
    cli_main(["--source", "all", "--repo-root", str(fake_repo), "--out", str(out)])
    capsys.readouterr()
    assert cli_main(["--show", "--out", str(out)]) == 0
    shown = capsys.readouterr().out
    for name in EXPECTED_SOURCES:
        assert name in shown
