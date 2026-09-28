"""Маппинг UI-параметров → CLI-аргументы ML-скриптов (T-229).

Проблема: UI/БД оперируют тогглами (`use_poi`, `zero_night_pred_cap`) и
коэффициентами, а `ml/scripts/make_submission.py` ждёт CLI-флаги
(`--flags-file`, `--pred-cap`, `--zero-route`, ...).

Здесь — чистые функции (без Celery/DB), чтобы их можно было тестировать
юнит-тестами (clinerule 16: RED→GREEN→REFACTOR).

Соответствие флагов (ml/transit_ai/config/flags.py):
    use_poi        → features.use_poi_features
    use_weather    → features.use_weather
    use_events     → features.use_events
    use_seasonal   → features.use_seasonal_calendar
    use_traffic    → features.use_traffic
    use_lag        → (нет флага: lag встроен в xgboost_route, F-020)
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "FEATURE_FLAG_MAP",
    "build_flags_payload",
    "build_predict_args",
    "build_zero_args",
    "write_flags_file",
]

FEATURE_FLAG_MAP: dict[str, str] = {
    "use_poi": "use_poi_features",
    "use_weather": "use_weather",
    "use_events": "use_events",
    "use_seasonal": "use_seasonal_calendar",
    "use_traffic": "use_traffic",
}
"""DB feature_toggle → ML flags.yaml key. `use_lag` намеренно отсутствует."""

_DEFAULT_CAP_HOURS = [0, 1, 2, 3, 4]


def build_flags_payload(
    feature_flags: Mapping[str, bool] | None,
) -> dict[str, dict[str, bool]] | None:
    """Тогглы из БД → payload для flags.yaml (секция features).

    Returns:
        {"features": {...}} либо None, если тогглов нет (тогда — defaults.yaml).
    """
    if not feature_flags:
        return None
    features = {
        FEATURE_FLAG_MAP[name]: bool(value)
        for name, value in feature_flags.items()
        if name in FEATURE_FLAG_MAP
    }
    return {"features": features} if features else None


def write_flags_file(path: Path, payload: dict[str, Any]) -> Path:
    """Пишет flags.yaml (создаёт родительскую директорию)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


def build_zero_args(zero_overrides: Mapping[str, Mapping[str, Any]] | None) -> list[str]:
    """zero_overrides из БД → CLI-аргументы make_submission.py.

    Поддерживаются: zero_route_5, zero_night_pred_cap, zero_weekend, zero_holidays.
    """
    if not zero_overrides:
        return []

    args: list[str] = []
    if "zero_route_5" in zero_overrides:
        args += ["--zero-route", "5"]
    cap = zero_overrides.get("zero_night_pred_cap")
    if cap:
        pred_cap = cap.get("pred_cap")
        if pred_cap is not None:
            args += ["--pred-cap", str(int(pred_cap))]
            hours = cap.get("hours") or _DEFAULT_CAP_HOURS
            args += ["--cap-hours", *[str(int(h)) for h in hours]]
    if "zero_weekend" in zero_overrides:
        args.append("--zero-weekends")
    if "zero_holidays" in zero_overrides:
        args.append("--zero-holidays")
    return args


def build_predict_args(
    *,
    model_id: str,
    start_date: str,
    end_date: str,
    submission_id: str | None,
    coef_weather: float,
    coef_event: float,
    coef_season: float,
    model_kind: str = "xgboost_route",
    flags_file: Path | None = None,
    zero_args: list[str] | None = None,
    overrides_file: str | None = None,
    overrides_profile: str | None = None,
) -> list[str]:
    """Собирает argv для ml/scripts/make_submission.py."""
    args = [
        "--model-id",
        model_id,
        "--model-kind",
        model_kind,
        "--start-date",
        start_date.replace("-", ""),
        "--end-date",
        end_date.replace("-", ""),
        "--coef-weather",
        str(coef_weather),
        "--coef-event",
        str(coef_event),
        "--coef-season",
        str(coef_season),
    ]
    if submission_id:
        args += ["--submission-id", submission_id]
    if flags_file is not None:
        args += ["--flags-file", str(flags_file)]
    if overrides_file:
        args += ["--overrides-file", overrides_file]
    if overrides_profile:
        args += ["--overrides-profile", overrides_profile]
    args += list(zero_args or [])
    return args
