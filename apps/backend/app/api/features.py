"""Feature toggles + zero overrides API (T-195).

GET    /api/v1/features                    — list all toggles + overrides
POST   /api/v1/features/{name}/toggle      — переключить feature toggle
POST   /api/v1/zeros/{name}/toggle         — переключить zero override

Возвращает текущее состояние в БД. Фронт использует это для UI checkboxes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import FeatureToggle, ZeroOverride
from app.schemas.features import (
    FeaturesListResponse,
    FeatureToggleOut,
    FeatureToggleUpdate,
    ZeroOverrideOut,
    ZeroOverrideUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["features"])


@router.get(
    "/features",
    response_model=FeaturesListResponse,
    summary="List all feature toggles and zero overrides",
)
async def list_features(
    session: AsyncSession = Depends(get_db),
) -> FeaturesListResponse:
    """Возвращает текущее состояние ВСЕХ toggles + overrides из БД."""
    ft_stmt = select(FeatureToggle).order_by(FeatureToggle.name)
    zo_stmt = select(ZeroOverride).order_by(ZeroOverride.name)
    toggles = (await session.execute(ft_stmt)).scalars().all()
    overrides = (await session.execute(zo_stmt)).scalars().all()
    return FeaturesListResponse(
        feature_toggles=[FeatureToggleOut.model_validate(t) for t in toggles],
        zero_overrides=[ZeroOverrideOut.model_validate(o) for o in overrides],
    )


@router.post(
    "/features/{name}/toggle",
    response_model=FeatureToggleOut,
    summary="Toggle a feature on/off",
)
async def toggle_feature(
    name: str,
    body: FeatureToggleUpdate,
    session: AsyncSession = Depends(get_db),
) -> FeatureToggleOut:
    stmt = select(FeatureToggle).where(FeatureToggle.name == name)
    ft = (await session.execute(stmt)).scalar_one_or_none()
    if ft is None:
        raise HTTPException(status_code=404, detail=f"Feature '{name}' not found")
    ft.enabled = body.enabled
    await session.commit()
    await session.refresh(ft)
    return FeatureToggleOut.model_validate(ft)


@router.post(
    "/zeros/{name}/toggle",
    response_model=ZeroOverrideOut,
    summary="Toggle a zero override on/off",
)
async def toggle_zero(
    name: str,
    body: ZeroOverrideUpdate,
    session: AsyncSession = Depends(get_db),
) -> ZeroOverrideOut:
    stmt = select(ZeroOverride).where(ZeroOverride.name == name)
    zo = (await session.execute(stmt)).scalar_one_or_none()
    if zo is None:
        raise HTTPException(status_code=404, detail=f"Zero override '{name}' not found")
    zo.enabled = body.enabled
    if body.params is not None:
        zo.params = body.params
    await session.commit()
    await session.refresh(zo)
    return ZeroOverrideOut.model_validate(zo)
