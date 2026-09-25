"""Tests for validators_lookup.py (T-162)."""

from __future__ import annotations

from transit_ai.data.validators_lookup import (
    build_validators_lookup,
    get_validators_features,
    load_validators_lookup,
)


def test_build_validators_lookup_creates_csv() -> None:
    """T-162: build_validators_lookup пишет CSV кэш."""
    # Не запускаем полный train.csv — используем sample
    lookup = build_validators_lookup(use_cache_only=True)
    assert lookup.shape[0] > 0
    assert "route_id" in lookup.columns
    assert "weekday" in lookup.columns
    assert "hour" in lookup.columns
    assert "n_validators_mean" in lookup.columns
    assert "n_trams_mean" in lookup.columns


def test_load_validators_lookup_returns_correct_shape() -> None:
    """T-162: load_validators_lookup возвращает lookup DataFrame."""
    lookup = load_validators_lookup()
    # 9 routes × 7 weekday × 24 hours = 1512
    assert lookup.shape[0] == 1512
    assert lookup["route_id"].nunique() == 9  # routes 1,7,11,12,17,25,26,28,50
    assert lookup["weekday"].nunique() == 7
    assert lookup["hour"].nunique() == 24


def test_get_validators_features_for_route() -> None:
    """T-162: get_validators_features возвращает dict с n_validators и n_trams."""
    feats = get_validators_features(route_id=17, weekday=0, hour=8)
    assert "n_validators_mean" in feats
    assert "n_trams_mean" in feats
    assert feats["n_validators_mean"] > 0


def test_get_validators_features_missing_route_returns_zero() -> None:
    """T-162: route 5 нет в train → возвращает 0 (fallback)."""
    feats = get_validators_features(route_id=5, weekday=0, hour=8)
    assert feats["n_validators_mean"] == 0.0
    assert feats["n_trams_mean"] == 0.0
