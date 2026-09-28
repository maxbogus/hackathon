"""Tests for overrides_config (T-235): YAML-профили schedule-overrides.

Проверяем контракт между манифестом эталона (F-083) и кодом:
  - YAML-файл читается и валидируется pydantic-схемой
  - профили/дефолт/неизвестное имя → предсказуемые ошибки
  - apply_overrides применяет ровно свои даты/маршруты/часы и не мутирует вход
  - labels совпадают со стилем post_processing из манифеста A/B
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from transit_ai.calibration.overrides_config import (
    EventMultiplier,
    OverridesFile,
    OverridesProfile,
    PeriodMultiplier,
    apply_overrides,
    load_overrides,
    resolve_profile_name,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OVERRIDES_YAML = REPO_ROOT / "ml" / "configs" / "overrides" / "nov_dec_2025.yaml"


def _grid(dates: list[str], hours: list[int], routes: list[int]) -> pd.DataFrame:
    """Декартово произведение дат × часов × маршрутов (как build_full_grid)."""
    rows = [
        {"route": r, "date": date.fromisoformat(d), "hour": h}
        for d in dates
        for h in hours
        for r in routes
    ]
    return pd.DataFrame(rows)


# ─────────────────────────── YAML-файл и профили ───────────────────────────


def test_yaml_file_loaded_with_both_profiles() -> None:
    """Реальный файл содержит профили a_conservative и b_aggressive."""
    profile_a = load_overrides(OVERRIDES_YAML, "a_conservative")
    profile_b = load_overrides(OVERRIDES_YAML, "b_aggressive")

    assert len(profile_a.holiday_overrides) == 3
    assert len(profile_a.period_multipliers) == 1
    assert len(profile_b.vacation_multipliers) == 2
    assert len(profile_b.event_multipliers) == 5


def test_default_profile_resolves_to_conservative() -> None:
    """Без --overrides-profile берётся default_profile из файла."""
    import yaml

    spec = OverridesFile.model_validate(
        yaml.safe_load(OVERRIDES_YAML.read_text("utf-8"))
    )
    assert resolve_profile_name(spec) == "a_conservative"
    assert resolve_profile_name(spec, "b_aggressive") == "b_aggressive"


def test_unknown_profile_lists_available() -> None:
    """Неизвестный профиль: понятная ошибка со списком доступных."""
    with pytest.raises(ValueError, match="a_conservative"):
        load_overrides(OVERRIDES_YAML, "does_not_exist")


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_overrides(tmp_path / "absent.yaml", "a_conservative")


def test_ambiguous_file_requires_profile(tmp_path: Path) -> None:
    """Несколько профилей без default_profile → требуем явный выбор."""
    path = tmp_path / "many.yaml"
    path.write_text("profiles:\n  one: {}\n  two: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="несколько профилей"):
        load_overrides(path)


def test_invalid_spec_rejected_by_schema() -> None:
    """extra=forbid + проверки диапазонов/форм даты."""
    with pytest.raises(ValidationError):
        PeriodMultiplier.model_validate(
            {
                "name": "x",
                "start_date": "2025-12-31",
                "end_date": "2025-12-01",
                "multiplier": 0.9,
            }
        )
    with pytest.raises(ValidationError):
        EventMultiplier.model_validate(
            {
                "name": "x",
                "routes": [7],
                "multiplier": 1.1,
                "date": "2025-11-22",
                "start_date": "2025-11-22",
                "end_date": "2025-11-23",
            }
        )
    with pytest.raises(ValidationError):
        OverridesProfile.model_validate(
            {
                "holiday_overrides": [
                    {"date": "2025-11-03", "multiplier": 0.5, "junk": 1}
                ]
            }
        )


# ─────────────────────────── apply_overrides ───────────────────────────


def test_holiday_override_scales_only_target_date() -> None:
    """03.11 ×0.5: масштабирует только свою дату, прочие не трогает."""
    profile = load_overrides(OVERRIDES_YAML, "a_conservative")
    grid = _grid(["2025-11-02", "2025-11-03"], [12], [1])
    preds = np.array([100.0, 100.0])

    out, labels = apply_overrides(preds, grid, profile)

    assert out[0] == pytest.approx(100.0)  # 02.11 cold snap не покрывает
    assert out[1] == pytest.approx(50.0)  # 03.11 ×0.5
    assert "holiday_override_2025-11-03_mult_0.5" in labels


def test_cold_snap_label_matches_manifest_style() -> None:
    """Label cold snap: cold_snap_2025-12-23_to_2025-12-31_mult_0.92 (манифест A)."""
    profile = load_overrides(OVERRIDES_YAML, "a_conservative")
    grid = _grid(["2025-12-23"], [12], [1])

    _, labels = apply_overrides(np.array([200.0]), grid, profile)

    assert "cold_snap_2025-12-23_to_2025-12-31_mult_0.92" in labels


def test_cold_snap_scales_whole_period() -> None:
    """23–31.12 ×0.92 применимо и в первый, и в последний день диапазона."""
    profile = load_overrides(OVERRIDES_YAML, "a_conservative")
    grid = _grid(["2025-12-23", "2025-12-31", "2026-01-01"], [3], [50])
    preds = np.array([100.0, 100.0, 100.0])

    out, _ = apply_overrides(preds, grid, profile)

    assert out[0] == pytest.approx(92.0)
    assert out[1] == pytest.approx(
        0.7 * 0.92 * 100.0
    )  # 31.12: holiday ×0.7 и cold snap ×0.92
    assert out[2] == pytest.approx(100.0)  # вне submission-периода


def test_event_multiplier_applies_only_to_given_routes_and_hours() -> None:
    """Событие spartak_cska: маршруты 7/11/12/50, часы 15–20, ×1.10."""
    profile = load_overrides(OVERRIDES_YAML, "b_aggressive")
    grid = pd.DataFrame(
        [
            {"route": 7, "date": date(2025, 11, 22), "hour": 16},  # попадает
            {"route": 50, "date": date(2025, 11, 22), "hour": 20},  # попадает
            {"route": 7, "date": date(2025, 11, 22), "hour": 10},  # час мимо
            {"route": 1, "date": date(2025, 11, 22), "hour": 16},  # маршрут мимо
            {"route": 7, "date": date(2025, 11, 21), "hour": 16},  # дата мимо
        ]
    )
    preds = np.full(5, 100.0)

    out, labels = apply_overrides(preds, grid, profile)

    assert out[0] == pytest.approx(110.0)
    assert out[1] == pytest.approx(110.0)
    assert out[2] == pytest.approx(100.0)
    assert out[3] == pytest.approx(100.0)
    assert out[4] == pytest.approx(100.0)
    assert any(
        label.startswith("event_spartak_cska_2025-11-22_routes_7_11_12_50")
        for label in labels
    )


def test_vacation_multiplier_applies_to_school_hours_only() -> None:
    """Каникулы ×0.85 только в школьные часы (7–9, 13–16)."""
    profile = load_overrides(OVERRIDES_YAML, "b_aggressive")
    grid = _grid(["2025-11-02"], [8, 12], [1])
    preds = np.array([100.0, 100.0])

    out, labels = apply_overrides(preds, grid, profile)

    assert out[0] == pytest.approx(85.0)  # час 8 — школьный
    assert out[1] == pytest.approx(100.0)  # час 12 — нет
    assert any(
        "vacation_autumn" in label and "school_hours" in label for label in labels
    )


def test_labels_order_matches_documented_pipeline() -> None:
    """Порядок labels: holidays → period → vacation → event (как в манифесте A/B)."""
    profile = load_overrides(OVERRIDES_YAML, "b_aggressive")
    grid = _grid(["2025-11-03", "2025-11-02"], [8], [7])

    _, labels = apply_overrides(np.array([100.0, 100.0]), grid, profile)

    kinds = [
        "holiday"
        if label.startswith("holiday_override")
        else "period"
        if label.startswith("cold_snap")
        else "vacation"
        if label.startswith("vacation")
        else "event"
        for label in labels
    ]
    assert kinds == sorted(kinds, key=["holiday", "period", "vacation", "event"].index)
    assert len(labels) == 3 + 1 + 2 + 5  # A-часть + cold snap + 2 каникул + 5 событий


def test_apply_overrides_does_not_mutate_input() -> None:
    """Иммутабельность: входной массив не меняется."""
    profile = load_overrides(OVERRIDES_YAML, "a_conservative")
    grid = _grid(["2025-11-03"], [12], [1])
    preds = np.array([100.0])
    before = preds.copy()

    apply_overrides(preds, grid, profile)

    np.testing.assert_array_equal(preds, before)


def test_empty_profile_is_noop() -> None:
    """Профиль без overrides → тот же массив и пустые labels."""
    profile = OverridesProfile()
    grid = _grid(["2025-11-03"], [12], [1])
    preds = np.array([100.0])

    out, labels = apply_overrides(preds, grid, profile)

    assert labels == []
    np.testing.assert_array_equal(out, preds)
