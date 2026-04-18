"""Standalone audit router.

This admin shell has no database layer installed. The queries layer
(``core_app.queries.audit``) requires ``psycopg`` and
``core_app.db.executor``, neither of which are present in this extracted
repo (see ``pyproject.toml``).

All endpoints that would require a live audit database fail explicitly with
structured 503 errors so that callers receive a truthful response rather
than a silent empty list or fabricated success.

The ``/production`` endpoint summarises the truthful system state: no audit
evidence source is connected.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

_NO_DB_DETAIL = {
    "error": "audit_store_unavailable",
    "message": (
        "The audit data store is not available in this standalone admin shell. "
        "No database layer (psycopg / core_app.db) is configured. "
        "All audit operations must be performed through the core domain service."
    ),
}


@router.get("/production")
async def production_audit(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return the truthful production-readiness state of the audit subsystem.

    Because this admin shell has no database connection the audit subsystem
    is not operational. This endpoint always reflects that real state.
    """
    return {
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "production_ready": False,
        "summary": {
            "mode": "no-database",
            "message": (
                "No audit data store is connected in this standalone admin shell. "
                "psycopg and core_app.db are not installed. "
                "Audit evidence cannot be evaluated."
            ),
        },
    }


@router.get("/todos")
async def list_todos(
    _current_user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    """Return outstanding audit todos.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/issues")
async def list_issues(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return detected audit issues.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


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
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return a paginated list of audit logs.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/logs/{log_id}")
async def get_audit_log_detail(
    log_id: str,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return a single audit log entry by ID.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


# ──────────────────────────────────────────────────────────────────────
# Legal holds (T114)
# ──────────────────────────────────────────────────────────────────────


@router.post("/legal-holds", status_code=201)
async def create_legal_hold(
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Create a legal hold on a governed record.

    Raises 503 because no audit data store is connected in this admin shell.
    Legal holds require real persistence; fabricating a recorded-locally
    response is not acceptable.
    """
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for legal holds")
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.delete("/legal-holds/{hold_id}")
async def release_legal_hold(
    hold_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Release a legal hold.

    Raises 503 because no audit data store is connected in this admin shell.
    Returning a fabricated release confirmation is not acceptable.
    """
    if current_user.resolved_primary_role not in {"founder", "agency_admin", "compliance_reviewer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for legal holds")
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/legal-holds")
async def list_legal_holds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """List all active legal holds.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/chain/{resource}/{resource_id}")
async def audit_chain(
    resource: str,
    resource_id: str,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return the full audit chain for a governed resource.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/request/{request_id}")
async def audit_request_chain(
    request_id: str,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return all audit entries for a cross-domain request trace.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/evidence/{evidence_pack_id}")
async def audit_evidence_pack(
    evidence_pack_id: str,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return the audit entries attached to an evidence pack.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/retention")
async def audit_retention_summary(
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return a summary of audit retention policy state.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.get("/webhook-replays")
async def webhook_replay_status(
    limit: int = 25,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Return the status of pending or completed webhook replays.

    Raises 503 because no audit data store is connected in this admin shell.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)


@router.post("/webhook-replays/{webhook_id}")
async def request_webhook_replay(
    webhook_id: str,
    reason: str,
    _current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Request a replay of a specific webhook event.

    Raises 503 because no audit data store is connected in this admin shell.
    Fabricating a queued-local-shell response is not acceptable.
    """
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_NO_DB_DETAIL)
