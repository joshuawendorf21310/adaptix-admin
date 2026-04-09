"""Standalone audit router with truthful zero-state responses."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/production")
async def production_audit(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "production_ready": False,
        "summary": {
            "total_issues": 0,
            "critical": 0,
            "warnings": 0,
            "mode": "standalone-shell",
            "message": "No upstream production evidence source is connected in this extracted repo yet.",
        },
        "critical_issues": [],
        "details": {
            "empty_filters": [],
            "missing_error_handling": [],
            "hardcoded_values": [],
            "fake_implementations": [],
        },
    }


@router.get("/todos")
async def list_todos(
    _current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return []


@router.get("/issues")
async def list_issues(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "empty_filters": [],
        "missing_error_handling": [],
        "hardcoded_values": [],
        "fake_implementations": [],
    }


def _can_read_cross_tenant_audit(current_user: CurrentUser) -> bool:
    return current_user.resolved_primary_role in {"founder", "agency_admin", "compliance_reviewer", "supervisor"}


# ──────────────────────────────────────────────────────────────────────
# Paginated audit log query (T114)
# ──────────────────────────────────────────────────────────────────────


@router.get("/logs")
async def list_audit_logs(
    entity_type: str | None = Query(None, description="Filter by entity/resource type"),
    action: str | None = Query(None, description="Filter by action"),
    user_id: str | None = Query(None, description="Filter by actor user"),
    date_from: datetime | None = Query(None, description="Start date (inclusive)"),
    date_to: datetime | None = Query(None, description="End date (inclusive)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "items": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
        "filters": {
            "entity_type": entity_type,
            "action": action,
            "user_id": user_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
        "mode": "standalone-shell",
    }


@router.get("/logs/{log_id}")
async def get_audit_log_detail(
    log_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    raise HTTPException(status_code=404, detail=f"Audit log {log_id} not available in standalone shell mode")


# ──────────────────────────────────────────────────────────────────────
# Legal holds (T114)
# ──────────────────────────────────────────────────────────────────────


@router.post("/legal-holds", status_code=201)
async def create_legal_hold(
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions for legal holds")
    hold_id = uuid4()
    return {
        "status": "recorded-locally",
        "hold_id": str(hold_id),
        "resource": body.get("resource", "legal_hold"),
        "reason": body.get("reason", ""),
    }


@router.delete("/legal-holds/{hold_id}")
async def release_legal_hold(
    hold_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions for legal holds")
    return {"status": "released", "hold_id": str(hold_id), "affected_entries": 0}


@router.get("/legal-holds")
async def list_legal_holds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "items": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
    }


@router.get("/chain/{resource}/{resource_id}")
async def audit_chain(
    resource: str,
    resource_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "request_id": None,
        "resource": resource,
        "resource_id": resource_id,
        "operations": [],
        "total": 0,
    }


@router.get("/request/{request_id}")
async def audit_request_chain(
    request_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "request_id": request_id,
        "operations": [],
        "total": 0,
    }


@router.get("/evidence/{evidence_pack_id}")
async def audit_evidence_pack(
    evidence_pack_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "evidence_pack_id": evidence_pack_id,
        "items": [],
        "total": 0,
    }


@router.get("/retention")
async def audit_retention_summary(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {
        "mode": "standalone-shell",
        "summary": "No retention store connected",
    }


@router.get("/webhook-replays")
async def webhook_replay_status(
    limit: int = 25,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {"items": [], "limit": limit}


@router.post("/webhook-replays/{webhook_id}")
async def request_webhook_replay(
    webhook_id: str,
    reason: str,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {"status": "queued-local-shell", "webhook_id": webhook_id, "reason": reason}
