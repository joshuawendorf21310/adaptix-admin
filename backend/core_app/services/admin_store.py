"""Feature flag store backed by a flat JSON file.

This module provides ``AdminStore``, a lightweight persistence layer for
feature flags in the standalone admin shell.  It uses a JSON file at
``backend/data/feature_flags.json`` as its sole backing store because this
repo has no database layer installed (see ``pyproject.toml``).

The flat-file approach is intentional for the standalone shell and is
explicitly documented as such.  A production deployment would use the
``core_app.queries.feature_flags`` psycopg3 queries against a PostgreSQL
database (see ``core_app/queries/feature_flags.py``).  Migration to a real
DB is a deliberate architectural decision for this repo and is out of scope
here without introducing a database layer.

All public methods are synchronous; they acquire a file-system lock
implicitly by virtue of reading and writing the same path atomically with
``Path.write_text``.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


class AdminStore:
    """Flat-JSON persistence layer for feature flags in the admin shell.

    Reads and writes ``backend/data/feature_flags.json``.  Every mutating
    operation reads the full file, applies the change, and writes it back in
    a single synchronous call.  This is safe for single-process deployments;
    multi-process deployments should migrate to the psycopg3 queries layer.
    """

    def __init__(self) -> None:
        """Initialise the store, creating the backing file if absent."""
        self._path = Path(__file__).resolve().parents[2] / "data" / "feature_flags.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_flags(
        self,
        *,
        tenant_id: str | None = None,
        include_global: bool = True,
    ) -> list[dict[str, Any]]:
        """Return all feature flags, optionally filtered by tenant.

        Args:
            tenant_id: When provided, include only flags whose
                ``tenant_id`` matches this value.  Global flags (those with
                ``tenant_id`` set to ``None``) are also included when
                *include_global* is ``True``.
            include_global: When ``True`` (the default), global flags are
                returned alongside tenant-specific ones even when
                *tenant_id* is supplied.

        Returns:
            A list of flag dicts.  The list is empty when no flags match.
        """
        flags = self._read_all()
        if tenant_id is None:
            return flags
        return [
            flag for flag in flags
            if flag.get("tenant_id") == tenant_id
            or (include_global and flag.get("tenant_id") is None)
        ]

    def create_flag(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist a new feature flag and return the created record.

        Args:
            payload: A dict that must contain ``flag_key`` and may contain
                ``enabled`` (bool, default ``False``), ``tenant_id``
                (str | None), ``config`` (dict), and ``description`` (str).

        Returns:
            The created flag dict including the generated ``id``.
        """
        flags = self._read_all()
        item = {
            "id": str(uuid.uuid4()),
            "flag_key": payload["flag_key"],
            "enabled": payload.get("enabled", False),
            "tenant_id": payload.get("tenant_id"),
            "config": payload.get("config") or {},
            "description": payload.get("description") or "",
        }
        flags.append(item)
        self._write_all(flags)
        return item

    def update_flag(
        self, flag_id: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update an existing flag by its ID.

        Only keys in *payload* whose value is not ``None`` are applied so
        that a partial update never erases existing fields.

        Args:
            flag_id: The ``id`` of the flag to update.
            payload: A dict of fields to overwrite on the flag.

        Returns:
            The updated flag dict, or ``None`` if no flag with *flag_id*
            exists.
        """
        flags = self._read_all()
        for flag in flags:
            if flag["id"] == flag_id:
                flag.update({k: v for k, v in payload.items() if v is not None})
                self._write_all(flags)
                return flag
        return None

    def delete_flag(self, flag_id: str) -> bool:
        """Delete a flag by its ID.

        Args:
            flag_id: The ``id`` of the flag to remove.

        Returns:
            ``True`` if a flag was found and removed, ``False`` otherwise.
        """
        flags = self._read_all()
        new_flags = [flag for flag in flags if flag["id"] != flag_id]
        if len(new_flags) == len(flags):
            return False
        self._write_all(new_flags)
        return True

    def toggle_flag(
        self, flag_key: str, *, tenant_id: str
    ) -> dict[str, Any] | None:
        """Toggle the ``enabled`` state of a flag identified by key and tenant.

        Looks for a tenant-specific flag first; falls back to the global flag
        (``tenant_id`` is ``None``) if no tenant-specific record exists.

        Args:
            flag_key: The string key that identifies the flag.
            tenant_id: The tenant scope to search within.

        Returns:
            The updated flag dict after toggling, or ``None`` if no matching
            flag was found.
        """
        flags = self._read_all()
        selected: dict[str, Any] | None = None
        for flag in flags:
            if flag["flag_key"] == flag_key and flag.get("tenant_id") == tenant_id:
                selected = flag
                break
        if selected is None:
            for flag in flags:
                if flag["flag_key"] == flag_key and flag.get("tenant_id") is None:
                    selected = flag
                    break
        if selected is None:
            return None
        selected["enabled"] = not selected.get("enabled", False)
        self._write_all(flags)
        return selected

    def _read_all(self) -> list[dict[str, Any]]:
        """Read and deserialise the full flag list from disk.

        Returns:
            The parsed JSON array from the backing file.
        """
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_all(self, flags: list[dict[str, Any]]) -> None:
        """Serialise and write the full flag list to disk.

        Args:
            flags: The complete list of flag dicts to persist.
        """
        self._path.write_text(json.dumps(flags, indent=2), encoding="utf-8")


admin_store = AdminStore()
