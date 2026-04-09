"""Standalone feature flag admin router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core_app.api.dependencies import CurrentUser, get_current_user
from core_app.services.admin_store import admin_store

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


class FeatureFlagPayload(BaseModel):
    flag_key: str
    enabled: bool = False
    tenant_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class FeatureFlagUpdate(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    description: str | None = None


def _is_founder(user: CurrentUser) -> bool:
    return user.role == "founder" or "founder" in user.roles


def _is_admin_or_founder(user: CurrentUser) -> bool:
    return _is_founder(user) or user.role in {"admin", "agency_admin"} or any(role in {"admin", "agency_admin"} for role in user.roles)


@router.get("")
async def list_feature_flags(current_user: CurrentUser = Depends(get_current_user)) -> list[dict[str, Any]]:
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")
    if _is_founder(current_user):
        return admin_store.list_flags()
    return admin_store.list_flags(tenant_id=current_user.tenant_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feature_flag(payload: FeatureFlagPayload, current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")
    if payload.tenant_id is None and not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founder can create global flags")
    item = payload.model_dump()
    if not _is_founder(current_user):
        item["tenant_id"] = current_user.tenant_id
    return admin_store.create_flag(item)


@router.put("/{flag_id}")
async def update_feature_flag(flag_id: str, payload: FeatureFlagUpdate, current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")
    existing = next((flag for flag in admin_store.list_flags() if flag["id"] == flag_id), None)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    if not _is_founder(current_user) and existing.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this flag")
    updated = admin_store.update_flag(flag_id, payload.model_dump())
    return updated or existing


@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_flag(flag_id: str, current_user: CurrentUser = Depends(get_current_user)) -> None:
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")
    existing = next((flag for flag in admin_store.list_flags() if flag["id"] == flag_id), None)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    if not _is_founder(current_user) and existing.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this flag")
    admin_store.delete_flag(flag_id)


@router.get("/evaluate")
async def evaluate_flags(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, dict[str, Any]]:
    flags = admin_store.list_flags() if _is_founder(current_user) else admin_store.list_flags(tenant_id=current_user.tenant_id)
    return {flag["flag_key"]: {"enabled": flag["enabled"], "config": flag.get("config", {})} for flag in flags}


@router.post("/{flag_key}/toggle")
async def toggle_feature_flag(flag_key: str, current_user: CurrentUser = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin_or_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or founder role required")
    toggled = admin_store.toggle_flag(flag_key, tenant_id=current_user.tenant_id)
    if toggled is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")
    return toggled
