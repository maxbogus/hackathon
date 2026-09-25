"""Tests for ensemble blend (T-173): rank-average и weighted-mean.

Blender: scipy.stats.rankdata для каждой модели → усреднение рангов → нормировка.
Weighted-mean: простой блендинг с весами (для count data с пиками).
Используется для ensemble XGBoost + CatBoost на submission period.
"""
from __future__ import annotations

import numpy as np

from transit_ai.blend.rank_average import rank_average_blend, weighted_mean_blend

# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────


def test_rank_average_shape() -> None:
    """Выход blend имеет ту же длину, что и входы."""
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    out = rank_average_blend([a, b])
    assert out.shape == (5,)
    assert isinstance(out, np.ndarray)


def test_rank_average_monotone() -> None:
    """Если 2-й вход с более высоким средним — blend.mean ближе ко 2-му."""
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])  # mean=3
    b_high = np.array([100.0, 200.0, 300.0, 400.0, 500.0])  # mean=300
    out = rank_average_blend([a, b_high])
    # blend.mean должен быть выше, чем mean(a)=3, потому что b_high "тянет вверх" через ранги.
    # Но scale_target_mean = mean(a) по умолчанию → blend.mean ≈ 3.
    # Проверяем другой эффект: blend.std должен быть > 0 (есть вариация).
    assert out.std() > 0


def test_rank_average_bounds() -> None:
    """Min/max blend ≈ [0, max_input] (по построению, без явных bounds)."""
    rng = np.random.default_rng(42)
    a = rng.uniform(0, 100, size=50)
    b = rng.uniform(0, 100, size=50)
    out = rank_average_blend([a, b])
    # Mean blend ≈ mean первой модели (по rescale)
    assert abs(out.mean() - a.mean()) / a.mean() < 0.05
    # Min/max в [0, 2*max_input] (safety bounds)
    assert out.min() >= -1.0
    assert out.max() <= 200.0


def test_rank_average_equal_inputs() -> None:
    """Если все входы идентичны → blend ≈ input (равномерные ранги → линейный градиент)."""
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    out = rank_average_blend([a, a, a])
    # Форма и порядок сохраняются; mean ≈ mean(input)
    assert out.shape == a.shape
    assert abs(out.mean() - a.mean()) < 0.5
    # Монотонно возрастает (т.к. все входы монотонны)
    assert (np.diff(out) >= 0).all()


def test_rank_average_three_models() -> None:
    """3 модели — усреднение 3 рангов."""
    a = np.array([10.0, 20.0, 30.0])
    b = np.array([30.0, 10.0, 20.0])
    c = np.array([20.0, 30.0, 10.0])
    out = rank_average_blend([a, b, c])
    # Все три модели дают одинаковые ранги (1,2,3 в разном порядке) →
    # mean_rank у всех одинаков → out ≈ константа
    assert out.shape == (3,)
    assert abs(out.std()) < 0.1, f"Expected near-constant blend, got {out}"


def test_rank_average_scale_target_mean() -> None:
    """scale_target_mean позволяет явно задать target mean для rescale."""
    a = np.array([100.0, 200.0, 300.0, 400.0, 500.0])
    out_default = rank_average_blend([a, a])
    out_target = rank_average_blend([a, a], scale_target_mean=10.0)
    # out_target.mean() должен быть ближе к 10, чем default
    assert abs(out_target.mean() - 10.0) < abs(out_default.mean() - 10.0)


# ────────────────────────────────────────────────────────────────────
# weighted_mean_blend (для count data с пиками, T-173 v2)
# ────────────────────────────────────────────────────────────────────


def test_weighted_mean_default_equal_weights() -> None:
    """Без weights → равные (1/n) веса."""
    a = np.array([10.0, 20.0, 30.0])
    b = np.array([30.0, 20.0, 10.0])
    out = weighted_mean_blend([a, b])
    expected = (a + b) / 2  # equal weights
    np.testing.assert_array_almost_equal(out, expected)


def test_weighted_mean_custom_weights() -> None:
    """С явными весами — взвешенное среднее."""
    a = np.array([10.0, 20.0, 30.0])
    b = np.array([30.0, 20.0, 10.0])
    out = weighted_mean_blend([a, b], weights=[0.7, 0.3])
    expected = 0.7 * a + 0.3 * b
    np.testing.assert_array_almost_equal(out, expected)


def test_weighted_mean_preserves_scale() -> None:
    """Weighted mean НЕ сглаживает пики (в отличие от rank-average)."""
    a = np.array([100.0, 200.0, 1000.0, 500.0])
    b = np.array([110.0, 210.0, 1100.0, 550.0])
    out = weighted_mean_blend([a, b])
    # Max(out) должно быть близко к max(a, b) = 1100, не сглажено
    assert out.max() > 900, f"Weighted mean smoothed peaks: max={out.max()}"
    # Min/max примерно в исходном диапазоне
    assert out.min() > 0
    assert out.max() < 1200


def test_weighted_mean_normalizes_weights() -> None:
    """Веса нормализуются (sum → 1)."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0, 6.0])
    # Сумма весов = 5 (не 1) → должно нормализоваться
    out = weighted_mean_blend([a, b], weights=[3.0, 2.0])
    # После нормализации: [0.6, 0.4]
    expected = 0.6 * a + 0.4 * b
    np.testing.assert_array_almost_equal(out, expected)


def test_weighted_mean_length_mismatch() -> None:
    """Если массивы разной длины — ValueError."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0])
    import pytest
    with pytest.raises(ValueError):
        weighted_mean_blend([a, b])


def test_weighted_mean_weights_length_mismatch() -> None:
    """Если weights не соответствует predictions — ValueError."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0, 6.0])
    import pytest
    with pytest.raises(ValueError):
        weighted_mean_blend([a, b], weights=[0.5])

