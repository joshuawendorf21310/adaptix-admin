"""Extended audit router with comprehensive governance capabilities (features 51-77)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core_app.api.dependencies import CurrentUser, get_current_user
from core_app.models.audit_extended import AuditEventType, AuditSeverity, LegalHoldStatus
from core_app.services.audit_service import audit_service

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class LegalHoldCreateRequest(BaseModel):
    case_id: str
    scope: str
    reason: str
    custodian_user_ids: list[str] = Field(default_factory=list)
    custodian_tenant_ids: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class ReplayCreateRequest(BaseModel):
    reason: str
    webhook_id: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    dry_run: bool = False


def _can_manage_legal_holds(user: CurrentUser) -> bool:
    return user.resolved_primary_role in {"founder", "agency_admin", "compliance_reviewer", "legal_hold_operator"}


def _can_manage_replay(user: CurrentUser) -> bool:
    return user.resolved_primary_role in {"founder", "agency_admin"}


# Feature 51: Audit shell endpoint
@router.get("/health")
async def audit_health(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 51: Audit service health check."""
    return {
        "status": "ok",
        "mode": "standalone-shell",
        "message": "Audit service running in standalone mode. Connect upstream evidence source for real audit data.",
    }


# Feature 52-53: Truthful zero-state and connected state
@router.get("/status")
async def audit_status(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 52-53: Audit connection status."""
    return {
        "mode": "standalone-shell",
        "upstream_connected": False,
        "message": "No upstream audit evidence source connected. All audit queries return truthful empty state.",
        "capabilities": {
            "local_admin_audit": True,
            "upstream_tenant_audit": False,
            "cross_tenant_audit": False,
        },
    }


# Feature 54-55: Audit event list and detail views
@router.get("/events")
async def list_audit_events(
    event_type: str | None = Query(None),
    action: str | None = Query(None),
    actor_user_id: str | None = Query(None),
    tenant_id: str | None = Query(None),
    domain: str | None = Query(None),
    severity: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 54: List audit events with filtering (features 56-62)."""
    event_type_enum = AuditEventType(event_type) if event_type else None
    severity_enum = AuditSeverity(severity) if severity else None

    return audit_service.list_events(
        event_type=event_type_enum,
        action=action,
        actor_user_id=actor_user_id,
        tenant_id=tenant_id,
        domain=domain,
        severity=severity_enum,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get("/events/{event_id}")
async def get_audit_event(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 55: Get audit event detail."""
    event = audit_service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit event not found in standalone shell mode. Connect upstream audit source.",
        )
    return event


# Feature 63-66: Export workflows
@router.post("/export")
async def export_audit_events(
    format: str = Query("json", regex="^(json|csv)$"),
    event_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 63-65: Export audit events (JSON/CSV)."""
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for audit export")

    event_type_enum = AuditEventType(event_type) if event_type else None
    return audit_service.export_events(format=format, event_type=event_type_enum, date_from=date_from, date_to=date_to)


@router.post("/evidence-packet")
async def create_evidence_packet(
    event_ids: list[str],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 66: Create audit evidence packet."""
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return audit_service.create_evidence_packet(event_ids, current_user.user_id)


# Feature 67-70: Chain of custody and correlation
@router.get("/chain/{resource_type}/{resource_id}")
async def get_audit_chain(
    resource_type: str,
    resource_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 67-70: Get audit chain with correlation IDs."""
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "events": [],
        "total": 0,
        "mode": "standalone-shell",
    }


# Feature 71-77: Replay workflows
@router.get("/replay-requests")
async def list_replay_requests(
    limit: int = Query(25, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 71: List replay requests."""
    if not _can_manage_replay(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return audit_service.list_replay_requests(limit)


@router.post("/replay-requests", status_code=status.HTTP_201_CREATED)
async def create_replay_request(
    payload: ReplayCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 72: Create replay request with dry-run support (feature 75)."""
    if not _can_manage_replay(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return audit_service.create_replay_request(
        requested_by=current_user.user_id,
        reason=payload.reason,
        webhook_id=payload.webhook_id,
        event_ids=payload.event_ids,
        dry_run=payload.dry_run,
    )


@router.post("/replay-requests/{replay_id}/authorize")
async def authorize_replay_request(
    replay_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 74: Authorize replay request."""
    if current_user.resolved_primary_role != "founder":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founders can authorize replays")

    authorized = audit_service.authorize_replay(replay_id, current_user.user_id)
    if not authorized:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replay request not found")
    return authorized


# Feature 78-90: Legal hold workflows
@router.post("/legal-holds", status_code=status.HTTP_201_CREATED)
async def create_legal_hold(
    payload: LegalHoldCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 79: Create legal hold."""
    if not _can_manage_legal_holds(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for legal holds")

    return audit_service.create_legal_hold(
        case_id=payload.case_id,
        scope=payload.scope,
        reason=payload.reason,
        created_by=current_user.user_id,
        custodian_user_ids=payload.custodian_user_ids,
        custodian_tenant_ids=payload.custodian_tenant_ids,
        expires_at=payload.expires_at,
    )


@router.get("/legal-holds")
async def list_legal_holds(
    status_filter: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 78: List legal holds."""
    if not _can_manage_legal_holds(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    status_enum = LegalHoldStatus(status_filter) if status_filter else None
    return audit_service.list_legal_holds(status=status_enum, skip=skip, limit=limit)


@router.post("/legal-holds/{hold_id}/release")
async def release_legal_hold(
    hold_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 81: Release legal hold."""
    if not _can_manage_legal_holds(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    released = audit_service.release_legal_hold(hold_id, current_user.user_id)
    if not released:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal hold not found")
    return released


@router.post("/legal-holds/{hold_id}/acknowledge")
async def acknowledge_legal_hold(
    hold_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 87: Acknowledge legal hold notice."""
    acknowledged = audit_service.acknowledge_legal_hold(hold_id, current_user.user_id)
    if not acknowledged:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal hold not found")
    return acknowledged
