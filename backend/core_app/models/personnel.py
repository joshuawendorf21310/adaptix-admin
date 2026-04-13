"""Personnel and access management models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AdminRoleType(str, Enum):
    """Admin role classifications."""
    FOUNDER = "founder"
    AGENCY_ADMIN = "agency_admin"
    COMPLIANCE_OFFICER = "compliance_officer"
    SECURITY_OFFICER = "security_officer"
    POLICY_MANAGER = "policy_manager"
    LEGAL_HOLD_OPERATOR = "legal_hold_operator"
    VIEWER = "viewer"


class AccountType(str, Enum):
    """Account type classifications."""
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    ADMIN = "admin"


class AdminAccount(BaseModel):
    """Admin account model."""
    user_id: str
    tenant_id: str
    account_type: AccountType = AccountType.USER
    primary_role: AdminRoleType
    additional_roles: list[AdminRoleType] = Field(default_factory=list)
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime
    created_by: str
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    tags: list[str] = Field(default_factory=list)


class RoleAssignment(BaseModel):
    """Role assignment model for audit trail."""
    id: str
    user_id: str
    tenant_id: str
    role: AdminRoleType
    assigned_by: str
    assigned_at: datetime
    expires_at: datetime | None = None
    revoked_by: str | None = None
    revoked_at: datetime | None = None
    reason: str
    approval_required: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None


class AccessRecertification(BaseModel):
    """Access recertification campaign."""
    id: str
    campaign_name: str
    target_roles: list[AdminRoleType]
    target_tenant_ids: list[str] = Field(default_factory=list)
    started_at: datetime
    started_by: str
    due_at: datetime
    completed_at: datetime | None = None
    total_accounts: int = 0
    reviewed_accounts: int = 0
    revoked_accounts: int = 0
