"""Extended personnel router with access management (features 121-131)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core_app.api.dependencies import CurrentUser, get_current_user
from core_app.models.personnel import AccountType, AdminRoleType
from core_app.services.personnel_service import personnel_service

router = APIRouter(prefix="/api/v1/personnel", tags=["personnel"])


class AdminAccountCreateRequest(BaseModel):
    user_id: str
    tenant_id: str
    primary_role: AdminRoleType
    account_type: AccountType = AccountType.USER
    additional_roles: list[AdminRoleType] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RoleAssignmentRequest(BaseModel):
    user_id: str
    tenant_id: str
    role: AdminRoleType
    reason: str
    expires_at: datetime | None = None
    approval_required: bool = False


class RecertificationCampaignRequest(BaseModel):
    campaign_name: str
    target_roles: list[AdminRoleType]
    target_tenant_ids: list[str] = Field(default_factory=list)
    due_at: datetime


def _is_founder_or_admin(user: CurrentUser) -> bool:
    return user.resolved_primary_role in {"founder", "agency_admin"}


# Feature 121: Personnel admin view
@router.get("/")
async def list_personnel(
    account_type: str | None = Query(None),
    is_active: bool | None = Query(None),
    tenant_id: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """Feature 121: List personnel/admin accounts."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    account_type_enum = AccountType(account_type) if account_type else None
    return personnel_service.list_accounts(
        account_type=account_type_enum,
        is_active=is_active,
        tenant_id=tenant_id,
    )


@router.get("/{user_id}")
async def get_personnel_account(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get single personnel account."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    account = personnel_service.get_account(user_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_personnel_account(
    payload: AdminAccountCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create personnel/admin account."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.create_account(
        user_id=payload.user_id,
        tenant_id=payload.tenant_id,
        primary_role=payload.primary_role,
        created_by=current_user.user_id,
        account_type=payload.account_type,
        additional_roles=payload.additional_roles,
        tags=payload.tags,
    )


# Feature 122: Personnel access review
@router.get("/access/review")
async def access_review_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 122: Personnel access review summary."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    all_accounts = personnel_service.list_accounts()
    privileged = personnel_service.get_privileged_accounts()
    service_accounts = personnel_service.get_service_accounts()
    inactive = personnel_service.get_inactive_accounts(days_threshold=90)

    return {
        "total_accounts": len(all_accounts),
        "active_accounts": len([a for a in all_accounts if a["is_active"]]),
        "privileged_accounts": len(privileged),
        "service_accounts": len(service_accounts),
        "inactive_accounts": len(inactive),
        "accounts_needing_review": len([a for a in all_accounts if not a.get("reviewed_at")]),
    }


# Feature 123: Privileged role review
@router.get("/access/privileged")
async def list_privileged_accounts(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """Feature 123: List privileged role accounts."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.get_privileged_accounts()


# Feature 124-125: Admin and service account inventory
@router.get("/inventory/admin")
async def admin_account_inventory(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """Feature 124: Admin account inventory."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.list_accounts(account_type=AccountType.ADMIN)


@router.get("/inventory/service-accounts")
async def service_account_inventory(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """Feature 125: Service account inventory."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.get_service_accounts()


# Feature 126-127: Role assignment review and approval
@router.get("/roles/assignments")
async def list_role_assignments(
    user_id: str | None = Query(None),
    tenant_id: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """Feature 126: Role assignment review."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.list_role_assignments(user_id=user_id, tenant_id=tenant_id)


@router.post("/roles/assign", status_code=status.HTTP_201_CREATED)
async def assign_role(
    payload: RoleAssignmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Assign a role to a user."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.assign_role(
        user_id=payload.user_id,
        tenant_id=payload.tenant_id,
        role=payload.role,
        assigned_by=current_user.user_id,
        reason=payload.reason,
        expires_at=payload.expires_at,
        approval_required=payload.approval_required,
    )


@router.post("/roles/{assignment_id}/approve")
async def approve_role_assignment(
    assignment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 127: Approve role assignment."""
    if current_user.resolved_primary_role != "founder":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founders can approve role assignments")

    approved = personnel_service.approve_role_assignment(assignment_id, current_user.user_id)
    if not approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
    return approved


@router.delete("/roles/{assignment_id}")
async def revoke_role(
    assignment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Revoke a role assignment."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    revoked = personnel_service.revoke_role(assignment_id, current_user.user_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
    return revoked


# Feature 128: Access recertification workflow
@router.post("/recertification", status_code=status.HTTP_201_CREATED)
async def create_recertification_campaign(
    payload: RecertificationCampaignRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 128: Create access recertification campaign."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.create_recertification_campaign(
        campaign_name=payload.campaign_name,
        target_roles=payload.target_roles,
        started_by=current_user.user_id,
        due_at=payload.due_at,
        target_tenant_ids=payload.target_tenant_ids,
    )


@router.get("/recertification")
async def list_recertification_campaigns(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """List recertification campaigns."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.list_recertification_campaigns()


# Feature 129-131: Detection of inactive, excessive, orphaned admins
@router.get("/detection/inactive")
async def detect_inactive_admins(
    days: int = Query(90, ge=1, le=365),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """Feature 129: Detect inactive admin accounts."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return personnel_service.get_inactive_accounts(days_threshold=days)


@router.post("/{user_id}/deactivate")
async def deactivate_account(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Deactivate an account."""
    if not _is_founder_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    deactivated = personnel_service.deactivate_account(user_id)
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return deactivated
