"""Audit service with truthful zero-state behavior for standalone mode."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core_app.models.audit_extended import AuditEvent, AuditEventType, AuditSeverity, LegalHold, LegalHoldStatus, ReplayRequest


class AuditService:
    """Service for audit events, legal holds, and replay with truthful standalone behavior."""

    def __init__(self) -> None:
        self._events_path = Path(__file__).resolve().parents[2] / "data" / "audit_events.json"
        self._holds_path = Path(__file__).resolve().parents[2] / "data" / "legal_holds.json"
        self._replays_path = Path(__file__).resolve().parents[2] / "data" / "replay_requests.json"

        for path in [self._events_path, self._holds_path, self._replays_path]:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("[]", encoding="utf-8")

    def list_events(
        self,
        *,
        event_type: AuditEventType | None = None,
        action: str | None = None,
        actor_user_id: str | None = None,
        tenant_id: str | None = None,
        domain: str | None = None,
        severity: AuditSeverity | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List audit events with filtering (standalone mode returns empty with mode indicator)."""
        # In standalone mode without upstream connection, return truthful empty state
        return {
            "items": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
            "filters": {
                "event_type": event_type.value if event_type else None,
                "action": action,
                "actor_user_id": actor_user_id,
                "tenant_id": tenant_id,
                "domain": domain,
                "severity": severity.value if severity else None,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
            "mode": "standalone-shell",
            "message": "No upstream audit evidence source connected. This is a shell endpoint for future integration.",
        }

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Get a single audit event (standalone mode returns None)."""
        # Truthful standalone behavior: no fabricated audit evidence
        return None

    def create_event_local(
        self,
        event_type: AuditEventType,
        action: str,
        actor_user_id: str,
        actor_tenant_id: str,
        actor_role: str,
        resource_type: str,
        description: str,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        domain: str | None = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Create a local audit event (for admin operations within this service)."""
        events = self._read_events()
        event = {
            "id": str(uuid4()),
            "event_type": event_type.value,
            "action": action,
            "severity": severity.value,
            "actor_user_id": actor_user_id,
            "actor_tenant_id": actor_tenant_id,
            "actor_role": actor_role,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "tenant_id": tenant_id,
            "domain": domain,
            "description": description,
            "details": details or {},
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        events.append(event)
        self._write_events(events)
        return event

    def export_events(
        self,
        format: str = "json",
        event_type: AuditEventType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Export audit events (standalone mode returns empty)."""
        return {
            "format": format,
            "events": [],
            "total": 0,
            "exported_at": datetime.now(UTC).isoformat(),
            "mode": "standalone-shell",
        }

    def create_evidence_packet(self, event_ids: list[str], created_by: str) -> dict[str, Any]:
        """Create an evidence packet (standalone mode returns shell response)."""
        return {
            "evidence_packet_id": str(uuid4()),
            "event_count": 0,
            "created_by": created_by,
            "created_at": datetime.now(UTC).isoformat(),
            "mode": "standalone-shell",
            "message": "Evidence packet shell created. Connect upstream audit source for real evidence.",
        }

    # Legal hold operations
    def create_legal_hold(
        self,
        case_id: str,
        scope: str,
        reason: str,
        created_by: str,
        custodian_user_ids: list[str] | None = None,
        custodian_tenant_ids: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a legal hold."""
        holds = self._read_holds()
        hold = {
            "id": str(uuid4()),
            "case_id": case_id,
            "scope": scope,
            "reason": reason,
            "status": LegalHoldStatus.ACTIVE.value,
            "custodian_user_ids": custodian_user_ids or [],
            "custodian_tenant_ids": custodian_tenant_ids or [],
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
            "released_at": None,
            "released_by": None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "notice_sent_at": None,
            "acknowledged_by": [],
            "acknowledged_at": {},
            "affected_event_count": 0,
            "evidence_packet_id": None,
        }
        holds.append(hold)
        self._write_holds(holds)
        return hold

    def release_legal_hold(self, hold_id: str, released_by: str) -> dict[str, Any] | None:
        """Release a legal hold."""
        holds = self._read_holds()
        for hold in holds:
            if hold["id"] == hold_id:
                hold["status"] = LegalHoldStatus.RELEASED.value
                hold["released_at"] = datetime.now(UTC).isoformat()
                hold["released_by"] = released_by
                self._write_holds(holds)
                return hold
        return None

    def list_legal_holds(self, status: LegalHoldStatus | None = None, skip: int = 0, limit: int = 50) -> dict[str, Any]:
        """List legal holds."""
        holds = self._read_holds()
        if status:
            holds = [h for h in holds if h["status"] == status.value]
        total = len(holds)
        items = holds[skip : skip + limit]
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def acknowledge_legal_hold(self, hold_id: str, user_id: str) -> dict[str, Any] | None:
        """Acknowledge receipt of legal hold notice."""
        holds = self._read_holds()
        for hold in holds:
            if hold["id"] == hold_id:
                if user_id not in hold["acknowledged_by"]:
                    hold["acknowledged_by"].append(user_id)
                hold["acknowledged_at"][user_id] = datetime.now(UTC).isoformat()
                self._write_holds(holds)
                return hold
        return None

    # Replay operations
    def create_replay_request(
        self,
        requested_by: str,
        reason: str,
        webhook_id: str | None = None,
        event_ids: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Create a replay request."""
        replays = self._read_replays()
        replay = {
            "id": str(uuid4()),
            "webhook_id": webhook_id,
            "event_ids": event_ids or [],
            "reason": reason,
            "requested_by": requested_by,
            "requested_at": datetime.now(UTC).isoformat(),
            "status": "pending",
            "dry_run": dry_run,
            "authorized_by": None,
            "authorized_at": None,
            "executed_at": None,
            "result": {},
        }
        replays.append(replay)
        self._write_replays(replays)
        return replay

    def authorize_replay(self, replay_id: str, authorized_by: str) -> dict[str, Any] | None:
        """Authorize a replay request."""
        replays = self._read_replays()
        for replay in replays:
            if replay["id"] == replay_id:
                replay["status"] = "authorized"
                replay["authorized_by"] = authorized_by
                replay["authorized_at"] = datetime.now(UTC).isoformat()
                self._write_replays(replays)
                return replay
        return None

    def list_replay_requests(self, limit: int = 25) -> dict[str, Any]:
        """List replay requests."""
        replays = self._read_replays()
        return {"items": replays[-limit:], "total": len(replays), "limit": limit}

    def _read_events(self) -> list[dict[str, Any]]:
        return json.loads(self._events_path.read_text(encoding="utf-8"))

    def _write_events(self, events: list[dict[str, Any]]) -> None:
        self._events_path.write_text(json.dumps(events, indent=2), encoding="utf-8")

    def _read_holds(self) -> list[dict[str, Any]]:
        return json.loads(self._holds_path.read_text(encoding="utf-8"))

    def _write_holds(self, holds: list[dict[str, Any]]) -> None:
        self._holds_path.write_text(json.dumps(holds, indent=2), encoding="utf-8")

    def _read_replays(self) -> list[dict[str, Any]]:
        return json.loads(self._replays_path.read_text(encoding="utf-8"))

    def _write_replays(self, replays: list[dict[str, Any]]) -> None:
        self._replays_path.write_text(json.dumps(replays, indent=2), encoding="utf-8")


audit_service = AuditService()
