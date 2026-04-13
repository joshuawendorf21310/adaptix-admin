"""Extended feature flag service with comprehensive governance capabilities."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core_app.models.feature_flag_extended import (
    FlagDependency,
    FlagSchedule,
    FlagState,
    FlagTargeting,
    FlagVariant,
    FeatureFlagExtended,
)


class FeatureFlagService:
    """Service for managing feature flags with full governance support."""

    def __init__(self) -> None:
        self._path = Path(__file__).resolve().parents[2] / "data" / "feature_flags_extended.json"
        self._audit_path = Path(__file__).resolve().parents[2] / "data" / "flag_audit.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")
        if not self._audit_path.exists():
            self._audit_path.write_text("[]", encoding="utf-8")

    def list_flags(
        self,
        *,
        tenant_id: str | None = None,
        state: FlagState | None = None,
        tags: list[str] | None = None,
        owner_user_id: str | None = None,
        include_global: bool = True,
    ) -> list[dict[str, Any]]:
        """List feature flags with filtering."""
        flags = self._read_all()
        result = []
        for flag in flags:
            if tenant_id is not None and flag.get("tenant_id") != tenant_id:
                if not (include_global and flag.get("tenant_id") is None):
                    continue
            if state is not None and flag.get("state") != state.value:
                continue
            if owner_user_id is not None and flag.get("owner_user_id") != owner_user_id:
                continue
            if tags is not None:
                flag_tags = set(flag.get("tags", []))
                if not flag_tags.intersection(tags):
                    continue
            result.append(flag)
        return result

    def get_flag(self, flag_id: str) -> dict[str, Any] | None:
        """Get a single flag by ID."""
        flags = self._read_all()
        return next((f for f in flags if f["id"] == flag_id), None)

    def create_flag(
        self,
        flag_key: str,
        created_by: str,
        tenant_id: str | None = None,
        description: str = "",
        enabled: bool = False,
        config: dict[str, Any] | None = None,
        targeting: dict[str, Any] | None = None,
        variants: list[dict[str, Any]] | None = None,
        schedule: dict[str, Any] | None = None,
        dependencies: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        owner_user_id: str | None = None,
        is_kill_switch: bool = False,
        requires_approval: bool = False,
    ) -> dict[str, Any]:
        """Create a new feature flag."""
        now = datetime.now(UTC)
        flag = {
            "id": str(uuid4()),
            "flag_key": flag_key,
            "enabled": enabled,
            "state": FlagState.DRAFT.value,
            "tenant_id": tenant_id,
            "description": description,
            "config": config or {},
            "targeting": targeting or {},
            "variants": variants or [],
            "schedule": schedule or {},
            "owner_user_id": owner_user_id,
            "tags": tags or [],
            "dependencies": dependencies or [],
            "is_kill_switch": is_kill_switch,
            "requires_approval": requires_approval,
            "approved_by": None,
            "approved_at": None,
            "created_at": now.isoformat(),
            "created_by": created_by,
            "updated_at": now.isoformat(),
            "updated_by": created_by,
            "version": 1,
        }
        flags = self._read_all()
        flags.append(flag)
        self._write_all(flags)
        self._audit_action(flag["id"], "created", created_by, tenant_id or "", "Flag created", {})
        return flag

    def update_flag(
        self,
        flag_id: str,
        updated_by: str,
        tenant_id: str,
        reason: str = "",
        **updates: Any,
    ) -> dict[str, Any] | None:
        """Update a feature flag with audit trail."""
        flags = self._read_all()
        for flag in flags:
            if flag["id"] == flag_id:
                old_values = {k: flag.get(k) for k in updates.keys()}
                flag.update({k: v for k, v in updates.items() if v is not None})
                flag["updated_at"] = datetime.now(UTC).isoformat()
                flag["updated_by"] = updated_by
                flag["version"] = flag.get("version", 1) + 1
                self._write_all(flags)
                self._audit_action(flag_id, "updated", updated_by, tenant_id, reason, {"old": old_values, "new": updates})
                return flag
        return None

    def delete_flag(self, flag_id: str, deleted_by: str, tenant_id: str, reason: str = "") -> bool:
        """Delete a feature flag with audit trail."""
        flags = self._read_all()
        new_flags = [f for f in flags if f["id"] != flag_id]
        if len(new_flags) == len(flags):
            return False
        self._write_all(new_flags)
        self._audit_action(flag_id, "deleted", deleted_by, tenant_id, reason, {})
        return True

    def toggle_flag(self, flag_id: str, toggled_by: str, tenant_id: str, reason: str = "") -> dict[str, Any] | None:
        """Toggle a feature flag on/off."""
        flags = self._read_all()
        for flag in flags:
            if flag["id"] == flag_id:
                old_enabled = flag.get("enabled", False)
                flag["enabled"] = not old_enabled
                flag["updated_at"] = datetime.now(UTC).isoformat()
                flag["updated_by"] = toggled_by
                flag["version"] = flag.get("version", 1) + 1
                self._write_all(flags)
                self._audit_action(
                    flag_id,
                    "toggled",
                    toggled_by,
                    tenant_id,
                    reason,
                    {"old_enabled": old_enabled, "new_enabled": flag["enabled"]},
                )
                return flag
        return None

    def approve_flag(self, flag_id: str, approved_by: str, tenant_id: str) -> dict[str, Any] | None:
        """Approve a feature flag for activation."""
        return self.update_flag(
            flag_id,
            approved_by,
            tenant_id,
            reason="Flag approved for activation",
            approved_by=approved_by,
            approved_at=datetime.now(UTC).isoformat(),
            state=FlagState.PUBLISHED.value,
        )

    def publish_flag(self, flag_id: str, published_by: str, tenant_id: str) -> dict[str, Any] | None:
        """Publish a feature flag."""
        return self.update_flag(flag_id, published_by, tenant_id, reason="Flag published", state=FlagState.PUBLISHED.value)

    def archive_flag(self, flag_id: str, archived_by: str, tenant_id: str) -> dict[str, Any] | None:
        """Archive a feature flag."""
        return self.update_flag(flag_id, archived_by, tenant_id, reason="Flag archived", state=FlagState.ARCHIVED.value)

    def evaluate_flag(self, flag_key: str, tenant_id: str | None, user_id: str | None = None) -> dict[str, Any]:
        """Evaluate a feature flag for a given context."""
        flags = self._read_all()
        matching_flag = None

        # Try tenant-specific flag first
        if tenant_id:
            for flag in flags:
                if flag["flag_key"] == flag_key and flag.get("tenant_id") == tenant_id:
                    matching_flag = flag
                    break

        # Fall back to global flag
        if not matching_flag:
            for flag in flags:
                if flag["flag_key"] == flag_key and flag.get("tenant_id") is None:
                    matching_flag = flag
                    break

        if not matching_flag:
            return {"enabled": False, "config": {}, "reason": "flag_not_found"}

        # Check schedule
        schedule = matching_flag.get("schedule", {})
        now = datetime.now(UTC)
        if schedule.get("start_at") and datetime.fromisoformat(schedule["start_at"]) > now:
            return {"enabled": False, "config": {}, "reason": "not_yet_started"}
        if schedule.get("end_at") and datetime.fromisoformat(schedule["end_at"]) < now:
            return {"enabled": False, "config": {}, "reason": "ended"}
        if schedule.get("expiry_at") and datetime.fromisoformat(schedule["expiry_at"]) < now:
            return {"enabled": False, "config": {}, "reason": "expired"}

        return {
            "enabled": matching_flag.get("enabled", False),
            "config": matching_flag.get("config", {}),
            "variants": matching_flag.get("variants", []),
            "reason": "evaluated",
        }

    def get_audit_trail(self, flag_id: str) -> list[dict[str, Any]]:
        """Get audit trail for a specific flag."""
        audit_entries = self._read_audit()
        return [entry for entry in audit_entries if entry["flag_id"] == flag_id]

    def get_stale_flags(self, days_threshold: int = 90) -> list[dict[str, Any]]:
        """Identify stale flags that haven't been updated recently."""
        flags = self._read_all()
        threshold = datetime.now(UTC).timestamp() - (days_threshold * 86400)
        stale = []
        for flag in flags:
            updated_at = datetime.fromisoformat(flag["updated_at"]).timestamp()
            if updated_at < threshold and flag.get("state") == FlagState.PUBLISHED.value:
                stale.append(flag)
        return stale

    def _audit_action(
        self,
        flag_id: str,
        action: str,
        actor_user_id: str,
        actor_tenant_id: str,
        reason: str,
        changes: dict[str, Any],
    ) -> None:
        """Record an audit entry for a flag action."""
        audit_entries = self._read_audit()
        entry = {
            "id": str(uuid4()),
            "flag_id": flag_id,
            "action": action,
            "actor_user_id": actor_user_id,
            "actor_tenant_id": actor_tenant_id,
            "reason": reason,
            "timestamp": datetime.now(UTC).isoformat(),
            "changes": changes,
        }
        audit_entries.append(entry)
        self._write_audit(audit_entries)

    def _read_all(self) -> list[dict[str, Any]]:
        """Read all flags from storage."""
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_all(self, flags: list[dict[str, Any]]) -> None:
        """Write all flags to storage."""
        self._path.write_text(json.dumps(flags, indent=2), encoding="utf-8")

    def _read_audit(self) -> list[dict[str, Any]]:
        """Read audit trail from storage."""
        return json.loads(self._audit_path.read_text(encoding="utf-8"))

    def _write_audit(self, audit_entries: list[dict[str, Any]]) -> None:
        """Write audit trail to storage."""
        self._audit_path.write_text(json.dumps(audit_entries, indent=2), encoding="utf-8")


feature_flag_service = FeatureFlagService()
