"""Extended feature flag router with complete governance capabilities (features 13-50)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core_app.api.dependencies import CurrentUser, get_current_user
from core_app.models.feature_flag_extended import FlagState
from core_app.services.feature_flag_service import feature_flag_service

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


class FeatureFlagCreateRequest(BaseModel):
    flag_key: str
    description: str = ""
    enabled: bool = False
    tenant_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    targeting: dict[str, Any] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    schedule: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    owner_user_id: str | None = None
    is_kill_switch: bool = False
    requires_approval: bool = False


class FeatureFlagUpdateRequest(BaseModel):
    enabled: bool | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    targeting: dict[str, Any] | None = None
    variants: list[dict[str, Any]] | None = None
    schedule: dict[str, Any] | None = None
    tags: list[str] | None = None
    state: str | None = None


def _is_founder(user: CurrentUser) -> bool:
    return user.role == "founder" or "founder" in user.roles


def _is_admin_or_founder(user: CurrentUser) -> bool:
    return _is_founder(user) or user.role in {"admin", "agency_admin"} or any(
        role in {"admin", "agency_admin"} for role in user.roles
    )


# Feature 13-16: Feature flag CRUD
@router.get("")
async def list_feature_flags(
    state: str | None = Query(None),
    tags: str | None = Query(None),
    owner_user_id: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Feature 14: Read feature flags with filtering."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    tag_list = tags.split(",") if tags else None
    flag_state = FlagState(state) if state else None

    if _is_founder(current_user):
        return feature_flag_service.list_flags(state=flag_state, tags=tag_list, owner_user_id=owner_user_id)
    return feature_flag_service.list_flags(
        tenant_id=current_user.tenant_id, state=flag_state, tags=tag_list, owner_user_id=owner_user_id
    )


@router.get("/{flag_id}")
async def get_feature_flag(
    flag_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 14: Read single feature flag."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    flag = feature_flag_service.get_flag(flag_id)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    if not _is_founder(current_user) and flag.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access this flag")

    return flag


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    payload: FeatureFlagCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 13: Create feature flag."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")
    if payload.tenant_id is None and not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founder can create global flags")

    tenant_id = payload.tenant_id if _is_founder(current_user) else current_user.tenant_id

    return feature_flag_service.create_flag(
        flag_key=payload.flag_key,
        created_by=current_user.user_id,
        tenant_id=tenant_id,
        description=payload.description,
        enabled=payload.enabled,
        config=payload.config,
        targeting=payload.targeting,
        variants=payload.variants,
        schedule=payload.schedule,
        dependencies=payload.dependencies,
        tags=payload.tags,
        owner_user_id=payload.owner_user_id,
        is_kill_switch=payload.is_kill_switch,
        requires_approval=payload.requires_approval,
    )


@router.put("/{flag_id}")
async def update_feature_flag(
    flag_id: str,
    payload: FeatureFlagUpdateRequest,
    reason: str = Query("", description="Reason for change"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 15: Update feature flag."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    flag = feature_flag_service.get_flag(flag_id)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    if not _is_founder(current_user) and flag.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this flag")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = feature_flag_service.update_flag(flag_id, current_user.user_id, current_user.tenant_id, reason, **updates)

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return updated


@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(
    flag_id: str,
    reason: str = Query("", description="Reason for deletion"),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Feature 16: Delete feature flag."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    flag = feature_flag_service.get_flag(flag_id)
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    if not _is_founder(current_user) and flag.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this flag")

    feature_flag_service.delete_flag(flag_id, current_user.user_id, current_user.tenant_id, reason)


# Feature 17-18: Toggle enable/disable
@router.post("/{flag_id}/toggle")
async def toggle_feature_flag(
    flag_id: str,
    reason: str = Query("", description="Reason for toggle"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 17-18: Toggle feature flag enable/disable."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    toggled = feature_flag_service.toggle_flag(flag_id, current_user.user_id, current_user.tenant_id, reason)
    if not toggled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return toggled


# Feature 19: Evaluation endpoint
@router.get("/evaluate/{flag_key}")
async def evaluate_feature_flag(
    flag_key: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 19: Evaluate feature flag."""
    tenant_id = None if _is_founder(current_user) else current_user.tenant_id
    return feature_flag_service.evaluate_flag(flag_key, tenant_id, current_user.user_id)


# Feature 30: Audit trail
@router.get("/{flag_id}/audit")
async def get_flag_audit_trail(
    flag_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Feature 30: Get feature flag audit trail."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    return feature_flag_service.get_audit_trail(flag_id)


# Feature 36: Rollback workflow
@router.post("/{flag_id}/rollback")
async def rollback_feature_flag(
    flag_id: str,
    reason: str = Query(..., description="Reason for rollback"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 36: Rollback feature flag to previous state."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    # Disable flag immediately for rollback
    toggled = feature_flag_service.update_flag(
        flag_id, current_user.user_id, current_user.tenant_id, f"Rollback: {reason}", enabled=False
    )
    if not toggled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return toggled


# Feature 37: Stale flag detection
@router.get("/admin/stale-flags")
async def get_stale_flags(
    days: int = Query(90, ge=1, le=365),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Feature 37: Detect stale flags."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    return feature_flag_service.get_stale_flags(days)


# Feature 42-45: Approval workflow and states
@router.post("/{flag_id}/approve")
async def approve_feature_flag(
    flag_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 42: Approve feature flag for activation."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founders can approve flags")

    approved = feature_flag_service.approve_flag(flag_id, current_user.user_id, current_user.tenant_id)
    if not approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return approved


@router.post("/{flag_id}/publish")
async def publish_feature_flag(
    flag_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 44: Publish feature flag."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    published = feature_flag_service.publish_flag(flag_id, current_user.user_id, current_user.tenant_id)
    if not published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return published


@router.post("/{flag_id}/archive")
async def archive_feature_flag(
    flag_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Feature 45: Archive feature flag."""
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")

    archived = feature_flag_service.archive_flag(flag_id, current_user.user_id, current_user.tenant_id)
    if not archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return archived
