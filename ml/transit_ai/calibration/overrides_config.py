"""Schedule overrides config (T-235): YAML-профили постобработки submission.

Зачем: рецепт лучшего сабмита (holiday_override, cold_snap, vacation и event
multipliers) применялся ad-hoc вызовом функций из :mod:`schedule_overrides`
(см. F-127). Здесь этот рецепт становится **данными**: YAML-файл + профиль дают
детерминированную цепочку overrides и список labels для ``post_processing``
манифеста (clinerule 23).

Порядок применения (совпадает с манифестом эталона A, F-083)::

    holiday_overrides → period_multipliers → vacation_multipliers → event_multipliers

Использование::

    from transit_ai.calibration.overrides_config import apply_overrides, load_overrides

    profile = load_overrides(Path("ml/configs/overrides/nov_dec_2025.yaml"), "a_conservative")
    preds, labels = apply_overrides(preds, grid, profile)
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from transit_ai.calibration.schedule_overrides import (
    apply_event_multiplier,
    apply_holiday_override,
    apply_period_multiplier,
    apply_vacation_multiplier,
)

__all__ = [
    "EventMultiplier",
    "HolidayOverride",
    "OverridesFile",
    "OverridesProfile",
    "PeriodMultiplier",
    "VacationMultiplier",
    "apply_overrides",
    "load_overrides",
    "resolve_profile_name",
]

_MODEL_CONFIG = ConfigDict(extra="forbid", frozen=True)


def _fmt(multiplier: float) -> str:
    """Множитель в label: 0.5 -> '0.5', 1.0 -> '1' (как в манифестах F-083)."""
    return f"{float(multiplier):g}"


class HolidayOverride(BaseModel):
    """Множитель на конкретную дату для всех маршрутов (праздник/перенос)."""

    model_config = _MODEL_CONFIG

    date: dt.date
    multiplier: float = 0.0


class PeriodMultiplier(BaseModel):
    """Множитель на диапазон дат (cold snap, многодневное событие)."""

    model_config = _MODEL_CONFIG

    name: str
    start_date: dt.date
    end_date: dt.date
    multiplier: float
    routes: list[int] | None = None
    hours: list[int] | None = None

    @model_validator(mode="after")
    def _check_range(self) -> PeriodMultiplier:
        if self.end_date < self.start_date:
            raise ValueError(f"end_date {self.end_date} < start_date {self.start_date}")
        return self


class VacationMultiplier(BaseModel):
    """Множитель на школьные часы в каникулы."""

    model_config = _MODEL_CONFIG

    name: str
    start_date: dt.date
    end_date: dt.date
    school_hours: list[int]
    multiplier: float
    routes: list[int] | None = None

    @model_validator(mode="after")
    def _check_range(self) -> VacationMultiplier:
        if self.end_date < self.start_date:
            raise ValueError(f"end_date {self.end_date} < start_date {self.start_date}")
        return self


class EventMultiplier(BaseModel):
    """Множитель события: маршрут(ы) + дата(ы) + часы (матч, ярмарка)."""

    model_config = _MODEL_CONFIG

    name: str
    routes: list[int]
    multiplier: float
    date: dt.date | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    start_hour: int | None = None
    end_hour: int | None = None

    @model_validator(mode="after")
    def _check_date_form(self) -> EventMultiplier:
        single = self.date is not None
        multi = self.start_date is not None and self.end_date is not None
        if single == multi:
            raise ValueError("укажи либо date, либо пару start_date+end_date")
        if not self.routes:
            raise ValueError("routes не может быть пустым")
        if (self.start_hour is None) != (self.end_hour is None):
            raise ValueError("start_hour и end_hour задаются вместе")
        return self


class OverridesProfile(BaseModel):
    """Набор overrides одного профиля (например a_conservative / b_aggressive)."""

    model_config = _MODEL_CONFIG

    description: str = ""
    holiday_overrides: list[HolidayOverride] = []
    period_multipliers: list[PeriodMultiplier] = []
    vacation_multipliers: list[VacationMultiplier] = []
    event_multipliers: list[EventMultiplier] = []

    def is_empty(self) -> bool:
        """Профиль без единого override (no-op)."""
        return not (
            self.holiday_overrides
            or self.period_multipliers
            or self.vacation_multipliers
            or self.event_multipliers
        )


class OverridesFile(BaseModel):
    """Файл с профилями overrides (``ml/configs/overrides/*.yaml``)."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    default_profile: str | None = None
    profiles: dict[str, OverridesProfile]


def resolve_profile_name(spec: OverridesFile, requested: str | None = None) -> str:
    """Выбрать профиль: requested -> default_profile -> единственный в файле.

    Raises:
        ValueError: профиль не найден, либо выбор неоднозначен.
    """
    if requested is not None:
        if requested not in spec.profiles:
            raise ValueError(
                f"профиль {requested!r} не найден; доступны: {sorted(spec.profiles)}"
            )
        return requested
    if spec.default_profile is not None:
        if spec.default_profile not in spec.profiles:
            raise ValueError(
                f"default_profile {spec.default_profile!r} отсутствует в profiles "
                f"{sorted(spec.profiles)}"
            )
        return spec.default_profile
    if len(spec.profiles) == 1:
        return next(iter(spec.profiles))
    raise ValueError(
        f"в файле несколько профилей — укажи --overrides-profile: {sorted(spec.profiles)}"
    )


def load_overrides(
    path: str | Path,
    profile: str | None = None,
) -> OverridesProfile:
    """Прочитать YAML-файл overrides и вернуть выбранный профиль.

    Raises:
        FileNotFoundError: файла нет.
        ValueError: профиль не найден / выбор неоднозначен.
        pydantic.ValidationError: файл не соответствует схеме.
    """
    import yaml

    overrides_path = Path(path)
    if not overrides_path.is_file():
        raise FileNotFoundError(f"overrides-файл не найден: {overrides_path}")
    raw = yaml.safe_load(overrides_path.read_text(encoding="utf-8")) or {}
    spec = OverridesFile.model_validate(raw)
    name = resolve_profile_name(spec, profile)
    return spec.profiles[name]


def apply_overrides(
    predictions: np.ndarray,
    grid: pd.DataFrame,
    profile: OverridesProfile,
) -> tuple[np.ndarray, list[str]]:
    """Применить overrides профиля к predictions.

    Args:
        predictions: массив predictions (после bias-калибровки, pred_cap, zero_route).
        grid: DataFrame с колонками ``route``, ``date``, ``hour``.
        profile: профиль overrides.

    Returns:
        ``(predictions, labels)``: новый массив (>= 0) и labels в порядке
        применения — для поля ``post_processing`` манифеста.
    """
    preds = np.asarray(predictions, dtype=np.float64)
    labels: list[str] = []

    if profile.is_empty():
        return preds.copy(), labels

    route = grid["route"].astype(int)
    dates = grid["date"]
    hour = grid["hour"].astype(int)

    for holiday in profile.holiday_overrides:
        preds = apply_holiday_override(
            preds, route, dates, pd.Timestamp(holiday.date), holiday.multiplier
        )
        labels.append(
            f"holiday_override_{holiday.date.isoformat()}_mult_{_fmt(holiday.multiplier)}"
        )

    for period in profile.period_multipliers:
        preds = apply_period_multiplier(
            preds,
            route,
            dates,
            hour,
            pd.Timestamp(period.start_date),
            pd.Timestamp(period.end_date),
            period.multiplier,
            routes=period.routes,
            hours=period.hours,
        )
        labels.append(
            f"{period.name}_{period.start_date.isoformat()}"
            f"_to_{period.end_date.isoformat()}_mult_{_fmt(period.multiplier)}"
        )

    for vacation in profile.vacation_multipliers:
        preds = apply_vacation_multiplier(
            preds,
            route,
            dates,
            hour,
            pd.Timestamp(vacation.start_date),
            pd.Timestamp(vacation.end_date),
            vacation.school_hours,
            vacation.multiplier,
            routes=vacation.routes,
        )
        labels.append(
            f"{vacation.name}_{vacation.start_date.isoformat()}"
            f"_to_{vacation.end_date.isoformat()}_school_hours_mult_{_fmt(vacation.multiplier)}"
        )

    for event in profile.event_multipliers:
        for route_id in event.routes:
            preds = apply_event_multiplier(
                preds,
                route,
                dates,
                hour,
                route_id,
                event.multiplier,
                event_date=pd.Timestamp(event.date) if event.date is not None else None,
                start_date=pd.Timestamp(event.start_date) if event.start_date else None,
                end_date=pd.Timestamp(event.end_date) if event.end_date else None,
                start_hour=event.start_hour,
                end_hour=event.end_hour,
            )
        labels.append(_event_label(event))

    return np.maximum(preds, 0.0), labels


def _event_label(event: EventMultiplier) -> str:
    """Label события в стиле манифеста F-083 (event_<name>_<when>_routes_..._mult_...)."""
    routes_label = "_".join(str(r) for r in event.routes)
    if event.date is not None:
        when = event.date.isoformat()
    else:
        when = f"{event.start_date.isoformat()}_to_{event.end_date.isoformat()}"
    hours_suffix = (
        f"_h{event.start_hour}_{event.end_hour}"
        if event.start_hour is not None and event.end_hour is not None
        else ""
    )
    return f"event_{event.name}_{when}_routes_{routes_label}{hours_suffix}_mult_{_fmt(event.multiplier)}"
