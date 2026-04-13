"""Personnel and access management service."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core_app.models.personnel import AccessRecertification, AccountType, AdminAccount, AdminRoleType, RoleAssignment


class PersonnelService:
    """Service for managing admin accounts, roles, and access recertification."""

    def __init__(self) -> None:
        self._accounts_path = Path(__file__).resolve().parents[2] / "data" / "admin_accounts.json"
        self._assignments_path = Path(__file__).resolve().parents[2] / "data" / "role_assignments.json"
        self._recertifications_path = Path(__file__).resolve().parents[2] / "data" / "access_recertifications.json"

        for path in [self._accounts_path, self._assignments_path, self._recertifications_path]:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("[]", encoding="utf-8")

    def list_accounts(
        self,
        account_type: AccountType | None = None,
        is_active: bool | None = None,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List admin accounts."""
        accounts = self._read_accounts()
        if account_type:
            accounts = [a for a in accounts if a["account_type"] == account_type.value]
        if is_active is not None:
            accounts = [a for a in accounts if a["is_active"] == is_active]
        if tenant_id:
            accounts = [a for a in accounts if a["tenant_id"] == tenant_id]
        return accounts

    def get_account(self, user_id: str) -> dict[str, Any] | None:
        """Get a single admin account."""
        accounts = self._read_accounts()
        return next((a for a in accounts if a["user_id"] == user_id), None)

    def create_account(
        self,
        user_id: str,
        tenant_id: str,
        primary_role: AdminRoleType,
        created_by: str,
        account_type: AccountType = AccountType.USER,
        additional_roles: list[AdminRoleType] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new admin account."""
        accounts = self._read_accounts()
        account = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "account_type": account_type.value,
            "primary_role": primary_role.value,
            "additional_roles": [r.value for r in (additional_roles or [])],
            "is_active": True,
            "last_login_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
            "reviewed_at": None,
            "reviewed_by": None,
            "tags": tags or [],
        }
        accounts.append(account)
        self._write_accounts(accounts)
        return account

    def update_account(self, user_id: str, **updates: Any) -> dict[str, Any] | None:
        """Update an admin account."""
        accounts = self._read_accounts()
        for account in accounts:
            if account["user_id"] == user_id:
                account.update({k: v for k, v in updates.items() if v is not None})
                self._write_accounts(accounts)
                return account
        return None

    def deactivate_account(self, user_id: str) -> dict[str, Any] | None:
        """Deactivate an admin account."""
        return self.update_account(user_id, is_active=False)

    def get_inactive_accounts(self, days_threshold: int = 90) -> list[dict[str, Any]]:
        """Identify inactive admin accounts."""
        accounts = self._read_accounts()
        threshold = datetime.now(UTC).timestamp() - (days_threshold * 86400)
        inactive = []
        for account in accounts:
            if not account.get("is_active"):
                continue
            last_login = account.get("last_login_at")
            if last_login:
                last_login_ts = datetime.fromisoformat(last_login).timestamp()
                if last_login_ts < threshold:
                    inactive.append(account)
        return inactive

    def get_service_accounts(self) -> list[dict[str, Any]]:
        """List all service accounts."""
        return self.list_accounts(account_type=AccountType.SERVICE_ACCOUNT)

    def get_privileged_accounts(self) -> list[dict[str, Any]]:
        """List accounts with privileged roles."""
        accounts = self._read_accounts()
        privileged_roles = {AdminRoleType.FOUNDER.value, AdminRoleType.AGENCY_ADMIN.value, AdminRoleType.SECURITY_OFFICER.value}
        return [a for a in accounts if a["primary_role"] in privileged_roles or any(r in privileged_roles for r in a.get("additional_roles", []))]

    # Role assignment operations
    def assign_role(
        self,
        user_id: str,
        tenant_id: str,
        role: AdminRoleType,
        assigned_by: str,
        reason: str,
        expires_at: datetime | None = None,
        approval_required: bool = False,
    ) -> dict[str, Any]:
        """Assign a role to a user."""
        assignments = self._read_assignments()
        assignment = {
            "id": str(uuid4()),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role.value,
            "assigned_by": assigned_by,
            "assigned_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "revoked_by": None,
            "revoked_at": None,
            "reason": reason,
            "approval_required": approval_required,
            "approved_by": None,
            "approved_at": None,
        }
        assignments.append(assignment)
        self._write_assignments(assignments)
        return assignment

    def approve_role_assignment(self, assignment_id: str, approved_by: str) -> dict[str, Any] | None:
        """Approve a role assignment."""
        assignments = self._read_assignments()
        for assignment in assignments:
            if assignment["id"] == assignment_id:
                assignment["approved_by"] = approved_by
                assignment["approved_at"] = datetime.now(UTC).isoformat()
                self._write_assignments(assignments)
                return assignment
        return None

    def revoke_role(self, assignment_id: str, revoked_by: str) -> dict[str, Any] | None:
        """Revoke a role assignment."""
        assignments = self._read_assignments()
        for assignment in assignments:
            if assignment["id"] == assignment_id:
                assignment["revoked_by"] = revoked_by
                assignment["revoked_at"] = datetime.now(UTC).isoformat()
                self._write_assignments(assignments)
                return assignment
        return None

    def list_role_assignments(self, user_id: str | None = None, tenant_id: str | None = None) -> list[dict[str, Any]]:
        """List role assignments."""
        assignments = self._read_assignments()
        if user_id:
            assignments = [a for a in assignments if a["user_id"] == user_id]
        if tenant_id:
            assignments = [a for a in assignments if a["tenant_id"] == tenant_id]
        # Filter out revoked assignments
        return [a for a in assignments if a.get("revoked_at") is None]

    # Access recertification
    def create_recertification_campaign(
        self,
        campaign_name: str,
        target_roles: list[AdminRoleType],
        started_by: str,
        due_at: datetime,
        target_tenant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an access recertification campaign."""
        campaigns = self._read_recertifications()
        campaign = {
            "id": str(uuid4()),
            "campaign_name": campaign_name,
            "target_roles": [r.value for r in target_roles],
            "target_tenant_ids": target_tenant_ids or [],
            "started_at": datetime.now(UTC).isoformat(),
            "started_by": started_by,
            "due_at": due_at.isoformat(),
            "completed_at": None,
            "total_accounts": 0,
            "reviewed_accounts": 0,
            "revoked_accounts": 0,
        }
        campaigns.append(campaign)
        self._write_recertifications(campaigns)
        return campaign

    def list_recertification_campaigns(self) -> list[dict[str, Any]]:
        """List access recertification campaigns."""
        return self._read_recertifications()

    def complete_recertification_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        """Complete an access recertification campaign."""
        campaigns = self._read_recertifications()
        for campaign in campaigns:
            if campaign["id"] == campaign_id:
                campaign["completed_at"] = datetime.now(UTC).isoformat()
                self._write_recertifications(campaigns)
                return campaign
        return None

    def _read_accounts(self) -> list[dict[str, Any]]:
        return json.loads(self._accounts_path.read_text(encoding="utf-8"))

    def _write_accounts(self, accounts: list[dict[str, Any]]) -> None:
        self._accounts_path.write_text(json.dumps(accounts, indent=2), encoding="utf-8")

    def _read_assignments(self) -> list[dict[str, Any]]:
        return json.loads(self._assignments_path.read_text(encoding="utf-8"))

    def _write_assignments(self, assignments: list[dict[str, Any]]) -> None:
        self._assignments_path.write_text(json.dumps(assignments, indent=2), encoding="utf-8")

    def _read_recertifications(self) -> list[dict[str, Any]]:
        return json.loads(self._recertifications_path.read_text(encoding="utf-8"))

    def _write_recertifications(self, campaigns: list[dict[str, Any]]) -> None:
        self._recertifications_path.write_text(json.dumps(campaigns, indent=2), encoding="utf-8")


personnel_service = PersonnelService()
