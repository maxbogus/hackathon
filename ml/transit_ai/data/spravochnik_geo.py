"""Route geo-features из справочника остановок (T-156).

Источники:
1. data/real/spravochniki/Хакатон_справочники_трамвай_10_маршрутов.xlsx
   - 'Порядок_с_координатами' — route × stop × (lat, lon) для 5 валидных маршрутов
     (1, 5, 7, 11, 12; route_short_name ∈ {1,2,3,4,5,6,7,10,11,12}, но submission
     требует {1,5,7,11,12,17,25,26,28,50}).
2. data/real/train.csv — place_id (код площадки/депо) per route, помогает
   привязать route → primary_place_id.
3. ml/transit_ai/data/_user_routes_2025.json — user-provided data для
   маршрутов 17/25/26/28/50 (отсутствуют в GTFS).

Выход: DataFrame с колонками:
    route, n_stops, n_stops_per_dir,
    lat_first, lon_first, lat_last, lon_last, lat_mid, lon_mid,
    primary_place_id, dist_center_km.

Используется XGBoostRoutePredictor (T-156) как дополнительные фичи.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Координаты центра Москвы (Красная площадь)
MOSCOW_CENTER_LAT = 55.7558
MOSCOW_CENTER_LON = 37.6173

# 10 маршрутов хакатона (submission требует именно эти)
HACKATHON_ROUTES: tuple[int, ...] = (1, 5, 7, 11, 12, 17, 25, 26, 28, 50)

# Маршруты с данными в GTFS справочнике (route_short_name в 'Порядок_с_координатами')
ROUTES_IN_SPRAVOCHNIK: frozenset[int] = frozenset({1, 5, 7, 11, 12})

# Известные place_id (депо/площадки) из анализа train.csv
KNOWN_PLACE_IDS: frozenset[int] = frozenset({39706, 39707, 39708, 39709, 39710, 39711})

# primary_place_id per route (из анализа F-028: >97% транзакций на одно депо)
ROUTE_PRIMARY_PLACE_ID: dict[int, int] = {
    1: 39709,
    5: 39707,
    7: 39707,
    11: 39707,
    12: 39710,
    17: 39707,
    25: 39707,
    26: 39709,
    28: 39708,
    50: 39710,
}


def _repo_root() -> Path:
    """hackathon/ — корень репо."""
    return Path(__file__).resolve().parents[3]


def load_user_routes() -> dict[int, dict[str, Any]]:
    """Загрузить user-provided данные для маршрутов вне справочника.

    Returns:
        dict[int, dict]: ключ = route_id, значение = {n_stops, name, lat_*, lon_*}.
    """
    path = Path(__file__).parent / "_user_routes_2025.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw.items() if k != "_comment"}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Расстояние между двумя точками в км (haversine)."""
    R = 6371.0  # Earth radius km
    lat1_r, lat2_r = np.radians(lat1), np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def _read_xlsx_sheet(sheet_name: str) -> pd.DataFrame:
    """Прочитать лист из xlsx (без зависимости от openpyxl, используем pandas)."""
    path = (
        _repo_root()
        / "data"
        / "real"
        / "spravochniki"
        / "Хакатон_справочники_трамвай_10_маршрутов.xlsx"
    )
    # Если нет openpyxl в ml venv — читаем через системный python
    import subprocess
    import sys

    # Проверяем наличие openpyxl в текущем venv
    try:
        import openpyxl  # noqa: F401

        return pd.read_excel(path, sheet_name=sheet_name)
    except ImportError:
        pass
    # Fallback: запускаем системный python3 (там openpyxl установлен)
    result = subprocess.run(
        [sys.executable, "-c", _XLSX_READER_SCRIPT, str(path), sheet_name],
        check=True,
        capture_output=True,
        text=True,
    )
    return pd.read_json(result.stdout)


_XLSX_READER_SCRIPT = """
import json
import sys
import pandas as pd
path, sheet_name = sys.argv[1], sys.argv[2]
df = pd.read_excel(path, sheet_name=sheet_name)
# Convert all columns to string-friendly types
for c in df.columns:
    if df[c].dtype == 'datetime64[ns]':
        df[c] = df[c].astype(str)
    elif df[c].dtype == 'object':
        df[c] = df[c].astype(str)
print(df.to_json(orient='records', force_ascii=False))
"""


def _load_spravochnik_routes() -> pd.DataFrame:
    """Загрузить 5 маршрутов из GTFS 'Порядок_с_координатами'.

    Returns:
        DataFrame с колонками: route_short_name, stop_lat, stop_lon, stop_sequence.
        Только маршруты ∈ {1, 5, 7, 11, 12} (те, что в submission И в справочнике).
    """
    df = _read_xlsx_sheet("Порядок_с_координатами")
    df.columns = [
        "route_id",
        "route_short_name",
        "reg_num",
        "route_type",
        "trip_id",
        "trip_short_name",
        "direction_id",
        "start_date",
        "end_date",
        "stop_sequence",
        "stop_id",
        "actual_date",
        "stop_mode",
        "is_addpoint",
        "stop_name",
        "stop_lat",
        "stop_lon",
    ]
    df = df.iloc[1:].copy()
    df["route_short_name"] = df["route_short_name"].astype(str)
    df["stop_lat"] = pd.to_numeric(df["stop_lat"], errors="coerce")
    df["stop_lon"] = pd.to_numeric(df["stop_lon"], errors="coerce")
    df["direction_id"] = pd.to_numeric(df["direction_id"], errors="coerce")
    df["stop_sequence"] = pd.to_numeric(df["stop_sequence"], errors="coerce")
    df = df.dropna(subset=["stop_lat", "stop_lon", "stop_sequence"])
    df = df[df["route_short_name"].astype(int).isin(ROUTES_IN_SPRAVOCHNIK)]
    return df


def _aggregate_spravochnik_route(df: pd.DataFrame, route: int) -> dict[str, Any]:
    """Агрегировать координаты остановок одного маршрута из GTFS."""
    sub = df[df["route_short_name"].astype(int) == route]
    if sub.empty:
        return {}
    # Берём direction=0 (одно направление, чтобы не дублировать конечные)
    sub_d0 = sub[sub["direction_id"] == 0]
    if sub_d0.empty:
        sub_d0 = sub
    sub_d0 = sub_d0.sort_values("stop_sequence")
    first = sub_d0.iloc[0]
    last = sub_d0.iloc[-1]
    mid_idx = len(sub_d0) // 2
    mid = sub_d0.iloc[mid_idx]
    return {
        "n_stops": int(sub["stop_id"].nunique()),
        "n_stops_per_dir": int(sub_d0["stop_id"].nunique()),
        "lat_first": float(first["stop_lat"]),
        "lon_first": float(first["stop_lon"]),
        "lat_last": float(last["stop_lat"]),
        "lon_last": float(last["stop_lon"]),
        "lat_mid": float(mid["stop_lat"]),
        "lon_mid": float(mid["stop_lon"]),
    }


def _aggregate_user_route(route: int, info: dict[str, Any]) -> dict[str, Any]:
    """Координаты для маршрута из user-provided данных (17/25/26/28/50)."""
    return {
        "n_stops": int(info["n_stops"]),
        "n_stops_per_dir": info.get("n_stops_per_dir", info["n_stops"] // 2),
        "lat_first": float(info["lat_first"]),
        "lon_first": float(info["lon_first"]),
        "lat_last": float(info["lat_last"]),
        "lon_last": float(info["lon_last"]),
        "lat_mid": (float(info["lat_first"]) + float(info["lat_last"])) / 2.0,
        "lon_mid": (float(info["lon_first"]) + float(info["lon_last"])) / 2.0,
    }


def build_route_geo_features() -> pd.DataFrame:
    """Построить DataFrame geo-фичей для 10 маршрутов хакатона.

    Returns:
        DataFrame[10 rows × N cols]:
            - route (int): 1, 5, 7, 11, 12, 17, 25, 26, 28, 50
            - n_stops (int): общее число остановок
            - n_stops_per_dir (int): в одном направлении
            - lat_first/lon_first: координаты начальной остановки
            - lat_last/lon_last: координаты конечной остановки
            - lat_mid/lon_mid: координаты средней остановки
            - primary_place_id (int): код площадки/депо из анализа train.csv
            - dist_center_km (float): расстояние до центра Москвы (haversine)
            - source (str): "spravochnik" или "user"
    """
    user_routes = load_user_routes()
    spravochnik_df = _load_spravochnik_routes()

    rows: list[dict[str, Any]] = []
    for route in HACKATHON_ROUTES:
        if route in ROUTES_IN_SPRAVOCHNIK:
            agg = _aggregate_spravochnik_route(spravochnik_df, route)
            source = "spravochnik"
        else:
            if route not in user_routes:
                raise KeyError(f"Route {route} не в справочнике и нет user-data")
            agg = _aggregate_user_route(route, user_routes[route])
            source = "user"

        if not agg:
            raise ValueError(f"Empty aggregation for route {route}")

        lat_mid = agg["lat_mid"]
        lon_mid = agg["lon_mid"]
        dist_center = _haversine_km(
            lat_mid, lon_mid, MOSCOW_CENTER_LAT, MOSCOW_CENTER_LON
        )

        rows.append(
            {
                "route": int(route),
                "n_stops": agg["n_stops"],
                "n_stops_per_dir": agg["n_stops_per_dir"],
                "lat_first": agg["lat_first"],
                "lon_first": agg["lon_first"],
                "lat_last": agg["lat_last"],
                "lon_last": agg["lon_last"],
                "lat_mid": lat_mid,
                "lon_mid": lon_mid,
                "primary_place_id": int(ROUTE_PRIMARY_PLACE_ID[route]),
                "dist_center_km": float(dist_center),
                "source": source,
            }
        )

    return pd.DataFrame(rows)


__all__ = [
    "HACKATHON_ROUTES",
    "ROUTES_IN_SPRAVOCHNIK",
    "ROUTE_PRIMARY_PLACE_ID",
    "build_route_geo_features",
    "load_user_routes",
]
