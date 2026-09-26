"""Schemas для /features endpoints (T-195).

UI получает список доступных feature toggles и zero overrides,
может переключать их (POST).
"""

from __future__ import annotations

from pydantic import BaseModel


class FeatureToggleOut(BaseModel):
    """Один feature toggle."""

    name: str
    description: str
    enabled: bool
    is_default: bool

    model_config = {"from_attributes": True}


class FeatureToggleUpdate(BaseModel):
    """Запрос на переключение фичи."""

    enabled: bool


class ZeroOverrideOut(BaseModel):
    """Один zero override."""

    name: str
    description: str
    enabled: bool
    params: dict

    model_config = {"from_attributes": True}


class ZeroOverrideUpdate(BaseModel):
    """Запрос на переключение zero strategy."""

    enabled: bool
    params: dict | None = None


class FeaturesListResponse(BaseModel):
    """Ответ GET /features."""

    feature_toggles: list[FeatureToggleOut]
    zero_overrides: list[ZeroOverrideOut]
