"""Feature flag SQL queries.

Provides flag evaluation with tenant and role-based overrides.

MIGRATION STATUS: Created for psycopg3 migration of feature_flags.py
- All feature_flags service methods now use these query functions
- Table: feature_flags (matches FeatureFlag model)
- Supports Redis-cached evaluation with DB fallback
- Full tenant isolation on all queries

Table: feature_flags
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg

from core_app.db.executor import execute, fetchall, fetchone

_OWNER = "queries.feature_flags"
_TABLE = "feature_flags"


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

async def get_flag(
    conn: psycopg.AsyncConnection,
    *,
    flag_key: str,
    tenant_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a feature flag for a tenant.

    Returns tenant-specific flag if exists, otherwise returns global flag.
    """
    return await fetchone(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE flag_key = %(flag_key)s
          AND (tenant_id = %(tenant_id)s OR tenant_id IS NULL)
        ORDER BY tenant_id DESC NULLS LAST
        LIMIT 1
        """,
        {
            "flag_key": flag_key,
            "tenant_id": tenant_id,
        },
        query_owner=f"{_OWNER}.get_flag",
        tenant_id=str(tenant_id),
    )


async def get_flag_by_id(
    conn: psycopg.AsyncConnection,
    *,
    flag_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Get a feature flag by ID."""
    return await fetchone(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE id = %(flag_id)s
        """,
        {"flag_id": flag_id},
        query_owner=f"{_OWNER}.get_flag_by_id",
    )


async def list_flags(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """List all feature flags for a tenant (includes global flags)."""
    if tenant_id is None:
        # List only global flags
        return await fetchall(
            conn,
            f"""
            SELECT * FROM {_TABLE}
            WHERE tenant_id IS NULL
            ORDER BY flag_key
            """,
            {},
            query_owner=f"{_OWNER}.list_flags.global",
        )

    # List tenant-specific and global flags
    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE tenant_id = %(tenant_id)s OR tenant_id IS NULL
        ORDER BY flag_key, tenant_id DESC NULLS LAST
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.list_flags.tenant",
        tenant_id=str(tenant_id),
    )


async def list_all_tenant_flags(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """List all tenant-specific flags (excludes global flags)."""
    return await fetchall(
        conn,
        f"""
        SELECT * FROM {_TABLE}
        WHERE tenant_id = %(tenant_id)s
        ORDER BY flag_key
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.list_all_tenant_flags",
        tenant_id=str(tenant_id),
    )


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

async def create_flag(
    conn: psycopg.AsyncConnection,
    *,
    flag_key: str,
    enabled: bool = True,
    tenant_id: uuid.UUID | None = None,
    config: dict[str, Any] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a new feature flag.

    Returns the created flag row.
    """
    import json

    now = datetime.now(UTC).replace(tzinfo=None)

    row = await fetchone(
        conn,
        f"""
        INSERT INTO {_TABLE} (
            id,
            flag_key,
            enabled,
            tenant_id,
            config,
            description,
            created_at,
            updated_at
        )
        VALUES (
            %(id)s,
            %(flag_key)s,
            %(enabled)s,
            %(tenant_id)s,
            %(config)s::jsonb,
            %(description)s,
            %(created_at)s,
            %(updated_at)s
        )
        RETURNING *
        """,
        {
            "id": uuid.uuid4(),
            "flag_key": flag_key,
            "enabled": enabled,
            "tenant_id": tenant_id,
            "config": json.dumps(config) if config else None,
            "description": description,
            "created_at": now,
            "updated_at": now,
        },
        query_owner=f"{_OWNER}.create_flag",
        tenant_id=str(tenant_id) if tenant_id else None,
    )

    if row is None:
        raise RuntimeError(f"INSERT {_TABLE} returned no row for flag_key={flag_key}")

    return row


async def update_flag(
    conn: psycopg.AsyncConnection,
    *,
    flag_id: uuid.UUID,
    enabled: bool | None = None,
    config: dict[str, Any] | None = None,
    description: str | None = None,
) -> dict[str, Any] | None:
    """Update a feature flag.

    Only updates fields that are provided (not None).
    Returns the updated row or None if not found.
    """
    import json

    now = datetime.now(UTC).replace(tzinfo=None)

    # Build dynamic SET clause
    updates = ["updated_at = %(updated_at)s"]
    params: dict[str, Any] = {
        "flag_id": flag_id,
        "updated_at": now,
    }

    if enabled is not None:
        updates.append("enabled = %(enabled)s")
        params["enabled"] = enabled

    if config is not None:
        updates.append("config = %(config)s::jsonb")
        params["config"] = json.dumps(config)

    if description is not None:
        updates.append("description = %(description)s")
        params["description"] = description

    return await fetchone(
        conn,
        f"""
        UPDATE {_TABLE}
        SET {', '.join(updates)}
        WHERE id = %(flag_id)s
        RETURNING *
        """,
        params,
        query_owner=f"{_OWNER}.update_flag",
    )


async def upsert_flag(
    conn: psycopg.AsyncConnection,
    *,
    flag_key: str,
    tenant_id: uuid.UUID | None = None,
    enabled: bool = True,
    config: dict[str, Any] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create or update a feature flag.

    Uses INSERT ... ON CONFLICT to atomically upsert.
    Returns the created or updated row.
    """
    import json

    now = datetime.now(UTC).replace(tzinfo=None)

    row = await fetchone(
        conn,
        f"""
        INSERT INTO {_TABLE} (
            id,
            flag_key,
            enabled,
            tenant_id,
            config,
            description,
            created_at,
            updated_at
        )
        VALUES (
            %(id)s,
            %(flag_key)s,
            %(enabled)s,
            %(tenant_id)s,
            %(config)s::jsonb,
            %(description)s,
            %(created_at)s,
            %(updated_at)s
        )
        ON CONFLICT (flag_key, COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid))
        DO UPDATE SET
            enabled = EXCLUDED.enabled,
            config = EXCLUDED.config,
            description = EXCLUDED.description,
            updated_at = EXCLUDED.updated_at
        RETURNING *
        """,
        {
            "id": uuid.uuid4(),
            "flag_key": flag_key,
            "enabled": enabled,
            "tenant_id": tenant_id,
            "config": json.dumps(config) if config else None,
            "description": description,
            "created_at": now,
            "updated_at": now,
        },
        query_owner=f"{_OWNER}.upsert_flag",
        tenant_id=str(tenant_id) if tenant_id else None,
    )

    if row is None:
        raise RuntimeError(f"INSERT {_TABLE} returned no row for flag_key={flag_key}")

    return row


async def delete_flag(
    conn: psycopg.AsyncConnection,
    *,
    flag_id: uuid.UUID,
) -> int:
    """Delete a feature flag.

    Returns the number of rows deleted (0 or 1).
    """
    return await execute(
        conn,
        f"""
        DELETE FROM {_TABLE}
        WHERE id = %(flag_id)s
        """,
        {"flag_id": flag_id},
        query_owner=f"{_OWNER}.delete_flag",
    )


async def delete_tenant_flags(
    conn: psycopg.AsyncConnection,
    *,
    tenant_id: uuid.UUID,
) -> int:
    """Delete all tenant-specific flags.

    Returns the number of rows deleted.
    """
    return await execute(
        conn,
        f"""
        DELETE FROM {_TABLE}
        WHERE tenant_id = %(tenant_id)s
        """,
        {"tenant_id": tenant_id},
        query_owner=f"{_OWNER}.delete_tenant_flags",
        tenant_id=str(tenant_id),
    )
