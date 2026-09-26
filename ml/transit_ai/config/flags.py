"""Feature flags for ML pipeline (T-174).

Позволяет включать/выключать feature groups и models через YAML,
без правки кода. Используется для A/B тестов, ablation analysis
и отключения нерабочих фичей после того, как drift обнаружен
(local holdout != platform score, F-040, F-048).

Usage:
    from transit_ai.config.flags import FlagsRegistry

    # Defaults (= v9_events baseline, reproducible)
    registry = FlagsRegistry.default()

    # Custom config
    registry = FlagsRegistry.from_yaml(Path("configs/no_events.yaml"))

    if registry.features.use_poi_features:
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "_DEFAULTS_YAML_PATH",
    "FeatureFlags",
    "FlagsRegistry",
    "ModeFlags",
    "ModelFlags",
    "_load_yaml_flags",
]

# Путь к defaults.yaml (относительно ml/transit_ai/config/)
_CONFIG_DIR = Path(__file__).resolve().parent
_DEFAULTS_YAML_PATH = _CONFIG_DIR / "defaults.yaml"


# Feature flags (groups of features)


@dataclass(frozen=True)
class FeatureFlags:
    """Флаги для feature groups. Frozen = immutable после создания."""

    use_calendar_rf: bool = True  # T-148 holidays/weekend
    use_seasonal_calendar: bool = True  # T-160 school/vacation
    use_weather: bool = True  # T-161
    use_validators_lookup: bool = True  # T-162
    use_geo_features: bool = True  # T-156
    use_poi_features: bool = True  # T-168 (146 POI per-route)
    use_events: bool = True  # T-172 (8 infrastructure events)
    use_traffic: bool = False  # T-124 (будет в T-175, off by default)


# Model flags


@dataclass(frozen=True)
class ModelFlags:
    """Флаги для моделей в ensemble."""

    use_xgboost: bool = True
    use_catboost: bool = True
    use_gru: bool = False  # T-029 (будет в T-175)


# Mode flags (не фичи и не модели, а режимы pipeline)


@dataclass(frozen=True)
class ModeFlags:
    """Флаги для режимов pipeline."""

    blend_method: str = "weighted_mean"  # weighted_mean | rank_average
    use_recursive: bool = False  # T-153 rolling-window forecast
    use_per_route_bias: bool = True  # T-147 per-route log bias


# Registry


@dataclass(frozen=True)
class FlagsRegistry:
    """Container для всех трёх групп флагов."""

    features: FeatureFlags
    models: ModelFlags
    modes: ModeFlags

    @classmethod
    def default(cls) -> FlagsRegistry:
        """Загрузить defaults.yaml (если существует) или all-True defaults."""
        if _DEFAULTS_YAML_PATH.exists():
            return cls.from_yaml(_DEFAULTS_YAML_PATH)
        return cls(
            features=FeatureFlags(),
            models=ModelFlags(),
            modes=ModeFlags(),
        )

    @classmethod
    def from_yaml(cls, path: Path | str) -> FlagsRegistry:
        """Загрузить флаги из YAML файла.

        Args:
            path: путь к YAML файлу с секциями features/models/modes.

        Returns:
            FlagsRegistry с переопределёнными defaults.

        Raises:
            FileNotFoundError: если файл не существует.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"Flags YAML not found: {p}. Expected sections: features/models/modes."
            )
        raw = yaml.safe_load(path.read_text())
        loaded = _load_yaml_flags(raw or {})
        return cls(
            features=_apply_overrides(FeatureFlags(), loaded.get("features", {})),
            models=_apply_overrides(ModelFlags(), loaded.get("models", {})),
            modes=_apply_overrides(ModeFlags(), loaded.get("modes", {})),
        )


# Helpers


def _load_yaml_flags(yaml_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Нормализовать YAML в dict с секциями features/models/modes.

    Args:
        yaml_data: распарсенный YAML (или пустой dict).

    Returns:
        dict с ключами features/models/modes (всегда присутствуют).
        Неизвестные ключи сохраняются для forward compatibility.
    """
    return {
        "features": yaml_data.get("features", {}) or {},
        "models": yaml_data.get("models", {}) or {},
        "modes": yaml_data.get("modes", {}) or {},
    }


def _apply_overrides(
    dataclass_instance: Any,
    overrides: dict[str, Any],
) -> Any:
    """Применить overrides к dataclass (только известные поля).

    Args:
        dataclass_instance: экземпляр dataclass.
        overrides: dict с переопределениями.

    Returns:
        Новый экземпляр dataclass с применёнными overrides.
        Неизвестные ключи в overrides игнорируются.
    """
    valid_fields = {f.name for f in fields(dataclass_instance)}
    filtered = {k: v for k, v in overrides.items() if k in valid_fields}
    return replace(dataclass_instance, **filtered)
