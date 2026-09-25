"""Validators lookup из train.csv (T-162).

Агрегирует число валидаторов (device_no) и вагонов (garage_number) на (route, weekday, hour)
из data/real/train.csv через chunked read. Корреляция с boardings = 0.72-0.84 в train_only.

Используется как фича XGBoostRoutePredictor для submission period (где boardings
неизвестны, но паттерн выпуска вагонов стабилен).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

__all__ = [
    "build_validators_lookup",
    "get_validators_features",
    "load_validators_lookup",
]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CACHE_PATH = _REPO_ROOT / "data" / "external" / "validators_lookup.csv"
_TRAIN_CSV = _REPO_ROOT / "data" / "real" / "train.csv"


def build_validators_lookup(use_cache_only: bool = False) -> pd.DataFrame:
    """Построить lookup {route, weekday, hour} -> mean(n_validators, n_trams).

    Если use_cache_only=True и кэш есть — читает из кэша.
    Иначе читает train.csv через chunked read.

    Returns:
        DataFrame [1512 rows × 5 cols]:
            route_id, weekday, hour, n_validators_mean, n_trams_mean.
    """
    if use_cache_only and _CACHE_PATH.exists():
        return load_validators_lookup()

    if not _TRAIN_CSV.exists():
        raise FileNotFoundError(f"Train CSV not found: {_TRAIN_CSV}")

    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        _TRAIN_CSV,
        sep=";",
        chunksize=500_000,
        usecols=[
            "tran_date_time",
            "validation_result",
            "device_no",
            "garage_number",
            "ngpt_route",
        ],
    ):
        chunk = chunk[chunk["validation_result"] == 1].copy()
        chunk["route_id"] = chunk["ngpt_route"].str.extract(r"(\d+)").astype(int)
        chunk["timestamp"] = pd.to_datetime(chunk["tran_date_time"])
        chunk["weekday"] = chunk["timestamp"].dt.weekday
        chunk["hour"] = chunk["timestamp"].dt.hour
        agg = chunk.groupby(["route_id", "weekday", "hour"]).agg(
            n_validators=("device_no", "nunique"),
            n_trams=("garage_number", "nunique"),
        )
        chunks.append(agg)

    full = pd.concat(chunks)
    lookup = full.groupby(level=[0, 1, 2]).mean()
    lookup = lookup.reset_index()
    lookup.columns = [
        "route_id",
        "weekday",
        "hour",
        "n_validators_mean",
        "n_trams_mean",
    ]

    # Fallback: для каждого (route, weekday, hour) если данных нет — route-mean по этому route.
    route_means = lookup.groupby("route_id")[
        ["n_validators_mean", "n_trams_mean"]
    ].mean()
    routes_in_train = sorted(lookup["route_id"].unique())
    full_rows = []
    for route in routes_in_train:
        rm_v = (
            float(route_means.loc[route, "n_validators_mean"])
            if route in route_means.index
            else 0.0
        )
        rm_t = (
            float(route_means.loc[route, "n_trams_mean"])
            if route in route_means.index
            else 0.0
        )
        for wd in range(7):
            for h in range(24):
                sub = lookup[
                    (lookup["route_id"] == route)
                    & (lookup["weekday"] == wd)
                    & (lookup["hour"] == h)
                ]
                if sub.empty:
                    full_rows.append(
                        {
                            "route_id": route,
                            "weekday": wd,
                            "hour": h,
                            "n_validators_mean": rm_v,
                            "n_trams_mean": rm_t,
                        }
                    )
                else:
                    full_rows.append(
                        {
                            "route_id": route,
                            "weekday": wd,
                            "hour": h,
                            "n_validators_mean": float(
                                sub.iloc[0]["n_validators_mean"]
                            ),
                            "n_trams_mean": float(sub.iloc[0]["n_trams_mean"]),
                        }
                    )
    lookup = pd.DataFrame(full_rows)

    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(_CACHE_PATH, index=False)
    return lookup


def load_validators_lookup() -> pd.DataFrame:
    """Загрузить lookup из CSV кэша."""
    if not _CACHE_PATH.exists():
        return build_validators_lookup(use_cache_only=False)
    return pd.read_csv(_CACHE_PATH)


def get_validators_features(route_id: int, weekday: int, hour: int) -> dict[str, Any]:
    """Получить фичи n_validators и n_trams для (route, weekday, hour).

    Returns:
        dict с n_validators_mean, n_trams_mean (float).
        Если route не найден — возвращает 0.0.
    """
    lookup = load_validators_lookup()
    row = lookup[
        (lookup["route_id"] == route_id)
        & (lookup["weekday"] == weekday)
        & (lookup["hour"] == hour)
    ]
    if row.empty:
        return {"n_validators_mean": 0.0, "n_trams_mean": 0.0}
    r = row.iloc[0]
    return {
        "n_validators_mean": float(r["n_validators_mean"]),
        "n_trams_mean": float(r["n_trams_mean"]),
    }
