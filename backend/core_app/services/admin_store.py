from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


class AdminStore:
    def __init__(self) -> None:
        self._path = Path(__file__).resolve().parents[2] / "data" / "feature_flags.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def list_flags(self, *, tenant_id: str | None = None, include_global: bool = True) -> list[dict[str, Any]]:
        flags = self._read_all()
        if tenant_id is None:
            return flags
        return [
            flag for flag in flags
            if flag.get("tenant_id") == tenant_id or (include_global and flag.get("tenant_id") is None)
        ]

    def create_flag(self, payload: dict[str, Any]) -> dict[str, Any]:
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

    def update_flag(self, flag_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        flags = self._read_all()
        for flag in flags:
            if flag["id"] == flag_id:
                flag.update({k: v for k, v in payload.items() if v is not None})
                self._write_all(flags)
                return flag
        return None

    def delete_flag(self, flag_id: str) -> bool:
        flags = self._read_all()
        new_flags = [flag for flag in flags if flag["id"] != flag_id]
        if len(new_flags) == len(flags):
            return False
        self._write_all(new_flags)
        return True

    def toggle_flag(self, flag_key: str, *, tenant_id: str) -> dict[str, Any] | None:
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
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_all(self, flags: list[dict[str, Any]]) -> None:
        self._path.write_text(json.dumps(flags, indent=2), encoding="utf-8")


admin_store = AdminStore()