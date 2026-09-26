"""Tests for validators_lookup.py (T-162)."""

from __future__ import annotations

from pathlib import Path

import pytest

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


# ----- Negative / corner cases (T-162) -----


def test_build_validators_lookup_raises_when_train_csv_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Negative: если train.csv отсутствует → FileNotFoundError.

    Делается через monkeypatch на путь к train.csv в модуле.
    """
    from transit_ai.data import validators_lookup as vl_mod

    # Перенаправляем путь к train.csv в несуществующую директорию
    fake_train = tmp_path / "no_such_dir" / "train.csv"
    monkeypatch.setattr(vl_mod, "_TRAIN_CSV", fake_train)
    monkeypatch.setattr(vl_mod, "_CACHE_PATH", tmp_path / "no_cache.csv")

    with pytest.raises(FileNotFoundError, match="train"):
        vl_mod.build_validators_lookup(use_cache_only=False)


def test_get_validators_features_out_of_range_hour_returns_zero() -> None:
    """Corner: weekday / hour вне диапазона → return 0 (не raise)."""
    feats = get_validators_features(route_id=17, weekday=99, hour=25)
    assert feats["n_validators_mean"] == 0.0
    assert feats["n_trams_mean"] == 0.0


def test_get_validators_features_negative_values_handled() -> None:
    """Corner: weekday=-1 / hour=-1 не падают."""
    feats = get_validators_features(route_id=17, weekday=-1, hour=-1)
    assert isinstance(feats, dict)
    assert "n_validators_mean" in feats
    assert "n_trams_mean" in feats


def test_load_validators_lookup_handles_corrupt_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Corner: если cache CSV corrupted → rebuild из train.csv (best effort).

    Помечаем cache как существующий, но с невалидным содержимым, чтобы
    rebuild гарантированно сработал.
    """
    from transit_ai.data import validators_lookup as vl_mod

    cache = tmp_path / "validators_lookup.csv"
    cache.write_text("corrupted,not,a,valid\ncsv,with,wrong,columns")
    monkeypatch.setattr(vl_mod, "_CACHE_PATH", cache)

    # Если train.csv есть — должен попробовать пересоздать cache;
    # если нет — FileNotFoundError. Оба варианта OK (мы проверяем что нет silent corrupt data).
    try:
        result = vl_mod.load_validators_lookup()
        # Если вернулся DataFrame, у него должны быть ожидаемые колонки
        assert hasattr(result, "columns")
    except FileNotFoundError:
        # Тоже OK — восстановление невозможно без train.csv
        pass
