"""Production audit router."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models import AuditLog
from core_app.schemas.audit import (
    AuditLogListResponse,
    LegalHoldCreateRequest,
    LegalHoldResponse,
)
from core_app.schemas.auth import CurrentUser

from ..services.audit_service import AuditService
from ..services.production_audit import ProductionAuditService
from ..services.webhook_governance import WebhookGovernanceService
from ..services.webhook_inbox_service import WebhookInboxService

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/production")
async def production_audit(
    _db: Session = Depends(db_session_dependency),
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Generate production readiness audit report."""
    service = ProductionAuditService(backend_path="./backend")
    report = service.generate_audit_report()

    return {
        "audit_timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "production_ready": report["production_ready"],
        "summary": report["summary"],
        "critical_issues": [
            {"type": "empty_filter", "count": len(report["findings"]["empty_filters"])} if report["findings"]["empty_filters"] else None,
            {"type": "bare_except", "count": len(report["findings"]["error_handling"])} if report["findings"]["error_handling"] else None,
        ],
        "details": report["findings"] if report["summary"]["total_issues"] > 0 else None,
    }


@router.get("/todos")
async def list_todos(
    _db: Session = Depends(db_session_dependency),
    _current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """List all TODO/FIXME comments."""
    service = ProductionAuditService(backend_path="./backend")
    return service.find_todos()


@router.get("/issues")
async def list_issues(
    _db: Session = Depends(db_session_dependency),
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """List all critical issues."""
    service = ProductionAuditService(backend_path="./backend")
    return {
        "empty_filters": service.find_empty_filters(),
        "missing_error_handling": service.find_missing_error_handling(),
        "hardcoded_values": service.find_hardcoded_values(),
        "fake_implementations": service.find_fake_implementations(),
    }


def _can_read_cross_tenant_audit(current_user: CurrentUser) -> bool:
    return current_user.resolved_primary_role in {"founder", "agency_admin", "compliance_reviewer", "supervisor"}


# ──────────────────────────────────────────────────────────────────────
# Paginated audit log query (T114)
# ──────────────────────────────────────────────────────────────────────


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    entity_type: str | None = Query(None, description="Filter by entity/resource type"),
    action: str | None = Query(None, description="Filter by action"),
    user_id: UUID | None = Query(None, description="Filter by actor user"),
    date_from: datetime | None = Query(None, description="Start date (inclusive)"),
    date_to: datetime | None = Query(None, description="End date (inclusive)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Paginated, filterable audit log query. Tenant-scoped unless founder."""
    q = db.query(AuditLog)

    # Tenant isolation
    if not _can_read_cross_tenant_audit(current_user):
        q = q.filter(AuditLog.tenant_id == current_user.tenant_id)

    if entity_type:
        q = q.filter((AuditLog.resource == entity_type) | (AuditLog.entity_name == entity_type))
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id:
        q = q.filter((AuditLog.user_id == user_id) | (AuditLog.actor_user_id == user_id))
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)

    total = q.count()
    service = AuditService(db)
    rows = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

    return {
        "items": [service.serialize_log(row) for row in rows],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/logs/{log_id}")
async def get_audit_log_detail(
    log_id: UUID,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Single audit entry detail. Tenant-scoped unless founder."""
    entry = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Audit log not found")
    if not _can_read_cross_tenant_audit(current_user) and entry.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Audit log not found")
    service = AuditService(db)
    return service.serialize_log(entry)


# ──────────────────────────────────────────────────────────────────────
# Legal holds (T114)
# ──────────────────────────────────────────────────────────────────────


@router.post("/legal-holds", response_model=LegalHoldResponse, status_code=201)
async def create_legal_hold(
    body: LegalHoldCreateRequest,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create a legal hold entry. Only founders/admins can create holds."""
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions for legal holds")

    service = AuditService(db)
    hold_id = uuid4()
    entry = service.write(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action="legal_hold.create",
        resource=body.resource or "legal_hold",
        resource_id=body.resource_id,
        legal_hold=True,
        legal_hold_id=hold_id,
        notes=f"Legal hold: {body.reason}",
    )
    return service.serialize_log(entry)


@router.delete("/legal-holds/{hold_id}")
async def release_legal_hold(
    hold_id: UUID,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Release a legal hold. Founder/admin only."""
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions for legal holds")

    entries = (
        db.query(AuditLog)
        .filter(AuditLog.legal_hold_id == hold_id, AuditLog.legal_hold == True)  # noqa: E712
        .all()
    )
    if not entries:
        raise HTTPException(status_code=404, detail="Legal hold not found")

    service = AuditService(db)
    # Write release audit record
    service.write(
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        action="legal_hold.release",
        resource="legal_hold",
        resource_id=str(hold_id),
        notes=f"Released legal hold {hold_id}",
    )

    return {"status": "released", "hold_id": str(hold_id), "affected_entries": len(entries)}


@router.get("/legal-holds")
async def list_legal_holds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """List active legal holds. Tenant-scoped unless founder."""
    q = db.query(AuditLog).filter(
        AuditLog.legal_hold == True,  # noqa: E712
        AuditLog.action == "legal_hold.create",
    )
    if not _can_read_cross_tenant_audit(current_user):
        q = q.filter(AuditLog.tenant_id == current_user.tenant_id)

    total = q.count()
    service = AuditService(db)
    rows = q.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()

    return {
        "items": [service.serialize_log(row) for row in rows],
        "total": total,
    }


@router.get("/chain/{resource}/{resource_id}")
async def audit_chain(
    resource: str,
    resource_id: str,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    service = AuditService(db)
    logs = service.query_action_chain(resource, resource_id)
    if not _can_read_cross_tenant_audit(current_user):
        logs = [log for log in logs if log.tenant_id == current_user.tenant_id]
    return {
        "request_id": logs[0].request_id if logs else None,
        "resource": resource,
        "resource_id": resource_id,
        "operations": [service.serialize_log(log) for log in logs],
        "total": len(logs),
    }


@router.get("/request/{request_id}")
async def audit_request_chain(
    request_id: str,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    service = AuditService(db)
    logs = service.query_by_request_id(request_id)
    if not _can_read_cross_tenant_audit(current_user):
        logs = [log for log in logs if log.tenant_id == current_user.tenant_id]
    return {
        "request_id": request_id,
        "operations": [service.serialize_log(log) for log in logs],
        "total": len(logs),
    }


@router.get("/evidence/{evidence_pack_id}")
async def audit_evidence_pack(
    evidence_pack_id: str,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    service = AuditService(db)
    logs = service.query_by_evidence_pack(evidence_pack_id)
    if not _can_read_cross_tenant_audit(current_user):
        logs = [log for log in logs if log.tenant_id == current_user.tenant_id]
    return {
        "evidence_pack_id": evidence_pack_id,
        "items": [service.serialize_log(log) for log in logs],
        "total": len(logs),
    }


@router.get("/retention")
async def audit_retention_summary(
    db: Session = Depends(db_session_dependency),
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    service = AuditService(db)
    return service.get_retention_summary()


@router.get("/webhook-replays")
async def webhook_replay_status(
    limit: int = 25,
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    from core_app.models.webhooks import WebhookEvent

    governance = WebhookGovernanceService()
    rows = db.query(WebhookEvent).order_by(WebhookEvent.received_at.desc()).limit(limit).all()
    if not _can_read_cross_tenant_audit(current_user):
        rows = [row for row in rows if row.tenant_id in {None, current_user.tenant_id}]
    return {"items": [governance.build_replay_status(row) for row in rows]}


@router.post("/webhook-replays/{webhook_id}")
async def request_webhook_replay(
    webhook_id: str,
    reason: str,
    db: Session = Depends(db_session_dependency),
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    from uuid import UUID

    result = WebhookInboxService(db).request_replay(
        UUID(webhook_id),
        reason=reason,
        evidence_pack_id="webhook-replay",
        audit_log_id=None,
    )
    return result or {"status": "missing"}
