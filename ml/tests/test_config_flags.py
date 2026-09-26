"""Tests for feature flags (T-174).

Feature flags через YAML -> FeatureFlags dataclass -> отключают/включают
feature groups и models без правки кода.

Использование:
    from transit_ai.config.flags import FlagsRegistry, FeatureFlags
    registry = FlagsRegistry.default()       # defaults.yaml
    flags = registry.features                # FeatureFlags dataclass
    if flags.use_poi_features: ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from transit_ai.config.flags import (
    FeatureFlags,
    FlagsRegistry,
    ModeFlags,
    ModelFlags,
    _load_yaml_flags,
)

# YAML loader


def test_load_yaml_flags_returns_dict() -> None:
    yaml_data: dict[str, Any] = {
        "features": {"use_poi_features": True, "use_events": False},
        "models": {"use_xgboost": True},
        "modes": {"blend_method": "weighted_mean"},
    }
    flags = _load_yaml_flags(yaml_data)
    assert flags["features"]["use_poi_features"] is True
    assert flags["features"]["use_events"] is False
    assert flags["models"]["use_xgboost"] is True


def test_load_yaml_flags_missing_section_returns_empty() -> None:
    yaml_data: dict[str, Any] = {"features": {"use_poi_features": True}}
    flags = _load_yaml_flags(yaml_data)
    assert flags["features"]["use_poi_features"] is True
    assert flags["models"] == {}
    assert flags["modes"] == {}


def test_load_yaml_flags_allows_unknown_keys() -> None:
    yaml_data = {"features": {"use_poi_features": True, "use_future_xyz": "test"}}
    flags = _load_yaml_flags(yaml_data)
    assert flags["features"]["use_poi_features"] is True
    assert flags["features"]["use_future_xyz"] == "test"


# FeatureFlags dataclass


def test_feature_flags_all_default_true() -> None:
    flags = FeatureFlags()
    assert flags.use_calendar_rf is True
    assert flags.use_seasonal_calendar is True
    assert flags.use_weather is True
    assert flags.use_validators_lookup is True
    assert flags.use_geo_features is True
    assert flags.use_poi_features is True
    assert flags.use_events is True
    assert flags.use_traffic is False


def test_feature_flags_disable_one() -> None:
    flags = FeatureFlags(use_poi_features=False)
    assert flags.use_poi_features is False
    assert flags.use_events is True


def test_feature_flags_immutable() -> None:
    flags = FeatureFlags()
    with pytest.raises(Exception):
        flags.use_poi_features = False  # type: ignore[misc]


# FlagsRegistry


def test_flags_registry_default_returns_all_sections() -> None:
    registry = FlagsRegistry.default()
    assert isinstance(registry.features, FeatureFlags)
    assert isinstance(registry.models, ModelFlags)
    assert isinstance(registry.modes, ModeFlags)


def test_flags_registry_from_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "no_events.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "features": {"use_events": False, "use_poi_features": True},
                "models": {"use_catboost": False},
                "modes": {"blend_method": "rank_average"},
            }
        )
    )
    registry = FlagsRegistry.from_yaml(yaml_path)
    assert registry.features.use_events is False
    assert registry.features.use_poi_features is True
    assert registry.features.use_weather is True
    assert registry.models.use_catboost is False
    assert registry.modes.blend_method == "rank_average"


def test_flags_registry_from_yaml_file_not_found(tmp_path: Path) -> None:
    yaml_path = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError, match="Flags YAML not found"):
        FlagsRegistry.from_yaml(yaml_path)


def test_flags_registry_from_yaml_partial_override(tmp_path: Path) -> None:
    yaml_path = tmp_path / "partial.yaml"
    yaml_path.write_text(yaml.dump({"features": {"use_poi_features": False}}))
    registry = FlagsRegistry.from_yaml(yaml_path)
    assert registry.features.use_poi_features is False
    assert registry.features.use_events is True
    assert registry.models.use_xgboost is True


# Defaults file


def test_defaults_yaml_file_exists() -> None:
    from transit_ai.config.flags import _DEFAULTS_YAML_PATH

    assert _DEFAULTS_YAML_PATH.exists(), f"Missing: {_DEFAULTS_YAML_PATH}"


def test_defaults_yaml_matches_baseline() -> None:
    registry = FlagsRegistry.default()
    assert registry.features.use_calendar_rf is True
    assert registry.features.use_seasonal_calendar is True
    assert registry.features.use_weather is True
    assert registry.features.use_validators_lookup is True
    assert registry.features.use_geo_features is True
    assert registry.features.use_poi_features is True
    assert registry.features.use_traffic is False
    assert registry.models.use_xgboost is True
    assert registry.models.use_catboost is True
    assert registry.models.use_gru is False
