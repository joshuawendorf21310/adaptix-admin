"""Extended feature flag models for production-grade governance."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FlagState(str, Enum):
    """Feature flag lifecycle states."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class FlagTargeting(BaseModel):
    """Feature flag targeting configuration."""
    tenant_ids: list[str] = Field(default_factory=list)
    agency_ids: list[str] = Field(default_factory=list)
    user_ids: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    environments: list[str] = Field(default_factory=list)
    percentage_rollout: int | None = Field(default=None, ge=0, le=100)


class FlagVariant(BaseModel):
    """Feature flag variant configuration."""
    name: str
    value: Any
    weight: int = Field(default=100, ge=0, le=100)


class FlagSchedule(BaseModel):
    """Feature flag scheduling configuration."""
    start_at: datetime | None = None
    end_at: datetime | None = None
    expiry_at: datetime | None = None


class FlagDependency(BaseModel):
    """Feature flag dependency rule."""
    flag_key: str
    required_enabled: bool = True


class FlagAuditEntry(BaseModel):
    """Feature flag change audit entry."""
    id: str
    flag_id: str
    action: str
    actor_user_id: str
    actor_tenant_id: str
    reason: str
    timestamp: datetime
    changes: dict[str, Any] = Field(default_factory=dict)


class FeatureFlagExtended(BaseModel):
    """Extended feature flag model with all governance capabilities."""
    id: str
    flag_key: str
    enabled: bool = False
    state: FlagState = FlagState.DRAFT
    tenant_id: str | None = None
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)

    # Targeting
    targeting: FlagTargeting = Field(default_factory=FlagTargeting)
    variants: list[FlagVariant] = Field(default_factory=list)

    # Scheduling
    schedule: FlagSchedule = Field(default_factory=FlagSchedule)

    # Governance
    owner_user_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    dependencies: list[FlagDependency] = Field(default_factory=list)
    is_kill_switch: bool = False
    requires_approval: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None

    # Metadata
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int = 1
