"""Feature flag admin API router."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.feature_flags import FeatureFlag
from core_app.schemas.auth import CurrentUser
from core_app.schemas.feature_flags import (
    FeatureFlagCreate,
    FeatureFlagEvaluateResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
)
from core_app.services.feature_flags import FeatureFlagService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


def _is_founder(user: CurrentUser) -> bool:
    return user.role == "founder" or "founder" in user.roles


def _is_admin_or_founder(user: CurrentUser) -> bool:
    return _is_founder(user) or user.role == "admin" or "admin" in user.roles


# ------------------------------------------------------------------
# LIST
# ------------------------------------------------------------------
@router.get("", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """List feature flags. Founder sees all; admin sees own tenant + global."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    query = db.query(FeatureFlag)
    if not _is_founder(current_user):
        query = query.filter(
            or_(
                FeatureFlag.tenant_id == current_user.tenant_id,
                FeatureFlag.tenant_id.is_(None),
            )
        )
    return query.order_by(FeatureFlag.flag_key).all()


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------
@router.post("", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    payload: FeatureFlagCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Create a feature flag. Only founder can create global (tenant_id=None)."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    # Only founder can create global flags
    if payload.tenant_id is None and not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founder can create global flags")

    # Non-founder admin: force tenant_id to their own tenant
    if not _is_founder(current_user):
        payload.tenant_id = current_user.tenant_id

    flag = FeatureFlag(
        flag_key=payload.flag_key,
        enabled=payload.enabled,
        tenant_id=payload.tenant_id,
        config=payload.config.model_dump() if payload.config else {},
        description=payload.description,
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


# ------------------------------------------------------------------
# UPDATE
# ------------------------------------------------------------------
@router.put("/{flag_id}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_id: UUID,
    payload: FeatureFlagUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    # Tenant isolation: admin can only modify their own tenant flags
    if not _is_founder(current_user):
        if flag.tenant_id is None or flag.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this flag")

    if payload.enabled is not None:
        flag.enabled = payload.enabled
    if payload.config is not None:
        flag.config = payload.config.model_dump()
    if payload.description is not None:
        flag.description = payload.description

    db.commit()
    db.refresh(flag)
    return flag


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------
@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    flag_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    if not _is_founder(current_user):
        if flag.tenant_id is None or flag.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this flag")

    db.delete(flag)
    db.commit()


# ------------------------------------------------------------------
# EVALUATE — returns all flags for current user context
# ------------------------------------------------------------------
@router.get("/evaluate", response_model=FeatureFlagEvaluateResponse)
async def evaluate_flags(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = FeatureFlagService(db)
    flags = svc.evaluate_all(tenant_id=current_user.tenant_id, role=current_user.role)
    return FeatureFlagEvaluateResponse(flags=flags)


# ------------------------------------------------------------------
# TOGGLE — quick toggle for a flag by key
# ------------------------------------------------------------------
@router.post("/{flag_key}/toggle", response_model=FeatureFlagResponse)
async def toggle_feature_flag(
    flag_key: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    # Find tenant-specific first, then global
    flag = (
        db.query(FeatureFlag)
        .filter(
            FeatureFlag.flag_key == flag_key,
            or_(
                FeatureFlag.tenant_id == current_user.tenant_id,
                FeatureFlag.tenant_id.is_(None),
            ),
        )
        .order_by(FeatureFlag.tenant_id.desc())
        .first()
    )

    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    if not _is_founder(current_user):
        if flag.tenant_id is None or flag.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot toggle this flag")

    flag.enabled = not flag.enabled
    db.commit()
    db.refresh(flag)
    return flag
