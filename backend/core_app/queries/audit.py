"""Audit log SQL queries.

Provides high-throughput write path for audit logs using COPY-based bulk
ingest, plus read access for compliance review.

MIGRATION STATUS: Extended for psycopg3 migration of audit_service.py
- All audit_service methods now use these query functions
- Table: audit_logs (matches AuditLog model)
- Immutable records with checksum chain for tamper detection
- Full tenant isolation on all queries

Table: audit_logs
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from psycopg import sql as psql

from core_app.db.executor import copy_records_to_table, fetchall, fetchone, fetchval

_OWNER = "queries.audit"

# Table name — matches the Alembic-managed audit table
_TABLE = "audit_logs"


# ---------------------------------------------------------------------------
# Helper functions for checksum chain
# ---------------------------------------------------------------------------

def _default_retention_expiry() -> datetime:
    """Default retention expiry: 10 years from now."""
    return datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3650)


def _compute_checksum(previous_checksum: str | None, entry_data: dict) -> str:
    """Compute SHA-256 hash chain: H(previous_checksum || serialized_data)."""
    payload = json.dumps(entry_data, sort_keys=True, default=str)
    raw = (previous_checksum or "") + payload
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _coerce_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    """Coerce string or UUID to UUID, or return None."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

async def get_previous_checksum(
    conn: psycopg.AsyncConnection,
) -> str | None:
    """Fetch the checksum of the most recent audit entry for chain continuity."""
    result = await fetchval(
        conn,
        f"""
        SELECT checksum FROM {_TABLE}
        WHERE checksum IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {},
        query_owner=f"{_OWNER}.get_previous_checksum",
    )
    return result


async def get_audit_log_by_id(
    conn: psycopg.AsyncConnection,
    *,
    log_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> dict[str, Any] | None:
    """Get a single audit log by ID. Optionally filter by tenant_id."""
    params: dict[str, Any] = {"log_id": log_id}
    where_clauses = ["id = %(log_id)s"]

    if tenant_id is not None:
        where_clauses.append("tenant_id = %(tenant_id)s")
        params["tenant_id"] = tenant_id

    return await fetchone(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE {' AND '.join(where_clauses)}
        """,
        params,
        query_owner=f"{_OWNER}.get_audit_log_by_id",
        tenant_id=str(tenant_id) if tenant_id else None,
    )


async def get_audit_log_by_audit_event_id(
    conn: psycopg.AsyncConnection,
    *,
    audit_event_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a single audit log by its stable public audit event ID."""
    return await fetchone(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE audit_event_id = %(audit_event_id)s
        """,
        {"audit_event_id": audit_event_id},
        query_owner=f"{_OWNER}.get_audit_log_by_audit_event_id",
    )


async def query_by_resource(
    conn: psycopg.AsyncConnection,
    *,
    resource: str,
    resource_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query audit logs by resource type and optional resource ID."""
    params: dict[str, Any] = {"resource": resource, "skip": skip, "limit": limit}
    where_clauses = ["resource = %(resource)s"]

    if resource_id:
        where_clauses.append("resource_id = %(resource_id)s")
        params["resource_id"] = resource_id

    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at DESC
        OFFSET %(skip)s LIMIT %(limit)s
        """,
        params,
        query_owner=f"{_OWNER}.query_by_resource",
    )


async def query_by_user(
    conn: psycopg.AsyncConnection,
    *,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query audit logs by user ID."""
    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE user_id = %(user_id)s OR actor_user_id = %(user_id)s
        ORDER BY created_at DESC
        OFFSET %(skip)s LIMIT %(limit)s
        """,
        {"user_id": user_id, "skip": skip, "limit": limit},
        query_owner=f"{_OWNER}.query_by_user",
    )


async def query_by_tenant(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query audit logs by tenant ID."""
    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE tenant_id = %(tenant_id)s
        ORDER BY created_at DESC
        OFFSET %(skip)s LIMIT %(limit)s
        """,
        {"tenant_id": tenant_id, "skip": skip, "limit": limit},
        query_owner=f"{_OWNER}.query_by_tenant",
        tenant_id=str(tenant_id),
    )


async def query_action_chain(
    conn: psycopg.AsyncConnection,
    *,
    resource: str,
    resource_id: str,
    action: str | None = None,
) -> list[dict[str, Any]]:
    """Query audit chain for a resource, optionally filtered by action.

    Returns results in chronological order (oldest first).
    """
    params: dict[str, Any] = {"resource": resource, "resource_id": resource_id}
    where_clauses = ["resource = %(resource)s", "resource_id = %(resource_id)s"]

    if action:
        where_clauses.append("action = %(action)s")
        params["action"] = action

    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at ASC
        """,
        params,
        query_owner=f"{_OWNER}.query_action_chain",
    )


async def query_by_request_id(
    conn: psycopg.AsyncConnection,
    *,
    request_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query all audit logs by request_id for tracing chains.

    All operations in an incident→ePCR→claim workflow share the same request_id.
    This allows end-to-end tracing of the entire continuity chain.

    Returns results in chronological order (oldest first).
    """
    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE request_id = %(request_id)s
        ORDER BY created_at ASC
        OFFSET %(skip)s LIMIT %(limit)s
        """,
        {"request_id": request_id, "skip": skip, "limit": limit},
        query_owner=f"{_OWNER}.query_by_request_id",
    )


async def query_by_evidence_pack(
    conn: psycopg.AsyncConnection,
    *,
    evidence_pack_id: str,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query audit logs attached to a specific evidence pack."""
    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE evidence_pack_id = %(evidence_pack_id)s
        ORDER BY created_at ASC
        OFFSET %(skip)s LIMIT %(limit)s
        """,
        {"evidence_pack_id": evidence_pack_id, "skip": skip, "limit": limit},
        query_owner=f"{_OWNER}.query_by_evidence_pack",
    )


async def count_legal_holds_by_table(
    conn: psycopg.AsyncConnection,
) -> dict[str, int]:
    """Count legal holds across all governed tables.

    Returns counts for audit_logs, webhook_events, and communication_events.
    """
    # Count audit_logs legal holds
    audit_count = await fetchval(
        conn,
        f"""
        SELECT COUNT(*) FROM {_TABLE}
        WHERE legal_hold = true
        """,
        {},
        query_owner=f"{_OWNER}.count_legal_holds.audit_logs",
    ) or 0

    # Count webhook_events legal holds
    webhook_count = await fetchval(
        conn,
        """
        SELECT COUNT(*) FROM webhook_events
        WHERE legal_hold = true
        """,
        {},
        query_owner=f"{_OWNER}.count_legal_holds.webhook_events",
    ) or 0

    # Count communication_events legal holds
    comms_count = await fetchval(
        conn,
        """
        SELECT COUNT(*) FROM communication_events
        WHERE legal_hold = true
        """,
        {},
        query_owner=f"{_OWNER}.count_legal_holds.communication_events",
    ) or 0

    return {
        "audit_logs": int(audit_count),
        "webhook_events": int(webhook_count),
        "communication_events": int(comms_count),
    }


async def count_records_by_table(
    conn: psycopg.AsyncConnection,
) -> dict[str, int]:
    """Count total records in all governed tables."""
    # Count audit_logs
    audit_count = await fetchval(
        conn,
        f"SELECT COUNT(*) FROM {_TABLE}",
        {},
        query_owner=f"{_OWNER}.count_records.audit_logs",
    ) or 0

    # Count webhook_events
    webhook_count = await fetchval(
        conn,
        "SELECT COUNT(*) FROM webhook_events",
        {},
        query_owner=f"{_OWNER}.count_records.webhook_events",
    ) or 0

    # Count communication_events
    comms_count = await fetchval(
        conn,
        "SELECT COUNT(*) FROM communication_events",
        {},
        query_owner=f"{_OWNER}.count_records.communication_events",
    ) or 0

    return {
        "audit_logs": int(audit_count),
        "webhook_events": int(webhook_count),
        "communication_events": int(comms_count),
    }


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

async def write_audit_log(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    success: str = "success",
    outcome_code: str | None = None,
    structured_outcome: dict | None = None,
    error_message: str | None = None,
    evidence_pack_id: str | None = None,
    evidence_refs: list[str] | None = None,
    proof_refs: list[str] | None = None,
    retention_expires_at: datetime | None = None,
    legal_hold: bool = False,
    legal_hold_id: uuid.UUID | None = None,
    notes: str | None = None,
    event_type: str | None = None,
    event_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Write immutable audit log entry with checksum chain.

    All audit entries are immutable and form a tamper-evident chain via checksums.
    Returns the created audit log record.
    """
    # Get previous checksum for chain continuity
    previous_checksum = await get_previous_checksum(conn)

    # Compute checksum for this entry
    entry_data = {
        "tenant_id": str(tenant_id) if tenant_id else None,
        "user_id": str(user_id) if user_id else None,
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
    }
    checksum = _compute_checksum(previous_checksum, entry_data)

    # Generate IDs
    audit_event_id = uuid.uuid4()
    log_id = uuid.uuid4()

    # Prepare fields
    entity_id = _coerce_uuid(resource_id)
    field_changes = after_state
    final_correlation_id = correlation_id or request_id
    final_outcome_code = outcome_code or success
    final_retention = retention_expires_at or _default_retention_expiry()

    # Insert audit log
    row = await fetchone(
        conn,
        f"""
        INSERT INTO {_TABLE} (
            id, audit_event_id, tenant_id, user_id, actor_user_id,
            action, resource, resource_id, entity_name, entity_id,
            before_state, after_state, field_changes,
            ip_address, user_agent, request_id, correlation_id,
            success, outcome_code, structured_outcome, error_message,
            evidence_pack_id, evidence_refs, proof_refs,
            retention_expires_at, legal_hold, legal_hold_id,
            notes, event_type, event_id,
            checksum, previous_checksum,
            created_at, updated_at
        )
        VALUES (
            %(id)s, %(audit_event_id)s, %(tenant_id)s, %(user_id)s, %(actor_user_id)s,
            %(action)s, %(resource)s, %(resource_id)s, %(entity_name)s, %(entity_id)s,
            %(before_state)s::jsonb, %(after_state)s::jsonb, %(field_changes)s::jsonb,
            %(ip_address)s, %(user_agent)s, %(request_id)s, %(correlation_id)s,
            %(success)s, %(outcome_code)s, %(structured_outcome)s::jsonb, %(error_message)s,
            %(evidence_pack_id)s, %(evidence_refs)s::jsonb, %(proof_refs)s::jsonb,
            %(retention_expires_at)s, %(legal_hold)s, %(legal_hold_id)s,
            %(notes)s, %(event_type)s, %(event_id)s,
            %(checksum)s, %(previous_checksum)s,
            NOW(), NOW()
        )
        RETURNING *
        """,
        {
            "id": log_id,
            "audit_event_id": audit_event_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "actor_user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "entity_name": resource,
            "entity_id": entity_id,
            "before_state": json.dumps(before_state) if before_state else None,
            "after_state": json.dumps(after_state) if after_state else None,
            "field_changes": json.dumps(field_changes) if field_changes else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "correlation_id": final_correlation_id,
            "success": success,
            "outcome_code": final_outcome_code,
            "structured_outcome": json.dumps(structured_outcome) if structured_outcome else None,
            "error_message": error_message,
            "evidence_pack_id": evidence_pack_id,
            "evidence_refs": json.dumps(evidence_refs) if evidence_refs else None,
            "proof_refs": json.dumps(proof_refs) if proof_refs else None,
            "retention_expires_at": final_retention,
            "legal_hold": legal_hold,
            "legal_hold_id": legal_hold_id,
            "notes": notes,
            "event_type": event_type,
            "event_id": event_id,
            "checksum": checksum,
            "previous_checksum": previous_checksum,
        },
        query_owner=f"{_OWNER}.write_audit_log",
        tenant_id=str(tenant_id) if tenant_id else None,
    )

    if row is None:
        raise RuntimeError(f"INSERT {_TABLE} returned no row for audit_event_id={audit_event_id}")

    return row


async def record_audit_event(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID | str,
    event_type: str,
    actor_id: uuid.UUID | str | None = None,
    actor_email: str | None = None,
    diff_json: str | None = None,
    metadata: str | None = None,
) -> dict[str, Any]:
    """Insert a single audit event (legacy compatibility method).

    This is a simplified interface for backward compatibility with the old audit_events table.
    New code should use write_audit_log() for full feature support.

    Returns the inserted row.
    """
    event_id = uuid.uuid4()
    row = await fetchone(
        conn,
        f"""
        INSERT INTO {_TABLE} (
            id, audit_event_id, tenant_id, user_id,
            action, resource, resource_id,
            after_state, notes,
            created_at, updated_at
        )
        VALUES (
            %(id)s, %(audit_event_id)s, %(tenant_id)s, %(actor_id)s,
            %(event_type)s, %(entity_type)s, %(entity_id)s,
            %(metadata)s::jsonb, %(diff_json)s,
            NOW(), NOW()
        )
        RETURNING id, audit_event_id, tenant_id, user_id as actor_id,
                  action as event_type, resource as entity_type,
                  resource_id as entity_id, created_at as occurred_at
        """,
        {
            "id": event_id,
            "audit_event_id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "actor_id": str(actor_id) if actor_id else None,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "event_type": event_type,
            "diff_json": diff_json,
            "metadata": metadata,
        },
        query_owner=f"{_OWNER}.record_audit_event",
        tenant_id=str(tenant_id),
    )
    if row is None:
        raise RuntimeError(f"INSERT {_TABLE} returned no row for id={event_id}")
    return row


async def bulk_record_audit_events(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    events: list[dict[str, Any]],
) -> int:
    """Bulk-insert audit events via PostgreSQL COPY for high-throughput paths.

    Each event dict must have: entity_type, entity_id, event_type.
    Optional keys: actor_id, actor_email, diff_json, metadata.

    Returns the number of rows written.
    """
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    records = [
        (
            uuid.uuid4(),          # id
            uuid.uuid4(),          # audit_event_id
            str(tenant_id),        # tenant_id
            str(ev.get("actor_id")) if ev.get("actor_id") else None,  # user_id
            ev["event_type"],     # action
            ev["entity_type"],    # resource
            str(ev["entity_id"]), # resource_id
            ev.get("diff_json"),  # notes
            now,                   # created_at
            now,                   # updated_at
        )
        for ev in events
    ]

    return await copy_records_to_table(
        conn,
        _TABLE,
        records,
        columns=[
            "id", "audit_event_id", "tenant_id", "user_id",
            "action", "resource", "resource_id", "notes",
            "created_at", "updated_at",
        ],
        query_owner=f"{_OWNER}.bulk_record_audit_events",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Convenience functions for service compatibility
# ---------------------------------------------------------------------------

async def create_audit_log(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    action: str,
    entity_name: str,
    entity_id: uuid.UUID,
    field_changes: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Create an audit log entry (convenience wrapper for write_audit_log).

    This is a simplified interface matching the fire_property_service signature.
    Maps to the full write_audit_log function.

    Args:
        conn: Database connection
        tenant_id: Tenant UUID
        actor_user_id: User performing the action
        action: Action being performed (e.g., "property_created")
        entity_name: Entity type (e.g., "fire_property")
        entity_id: Entity UUID
        field_changes: Dictionary of changed fields and metadata
        correlation_id: Request correlation ID

    Returns:
        Created audit log record
    """
    return await write_audit_log(
        conn,
        tenant_id=tenant_id,
        user_id=actor_user_id,
        action=action,
        resource=entity_name,
        resource_id=str(entity_id),
        after_state=field_changes,
        correlation_id=correlation_id,
    )
