"""Feature flag service with Redis-backed evaluation and DB fallback.

MIGRATION STATUS: Hybrid sync/async with psycopg3 support
- is_enabled() + is_enabled_async() for flag evaluation
- evaluate_all() + evaluate_all_async() for multi-flag evaluation
- Sync methods use SQLAlchemy ORM (legacy/test mode)
- Async methods use psycopg3 via queries module (production mode)
- _legacy_mode flag controls routing (set by presence of db parameter)
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core_app.core.config import get_settings
from core_app.db import acquire
from core_app.models.feature_flags import FeatureFlag
from core_app.queries import feature_flags as ff_queries

logger = logging.getLogger(__name__)

_CACHE_TTL = 30  # seconds


def _get_redis() -> Any | None:
    """Return a Redis client if configured, else None."""
    try:
        import redis

        settings = get_settings()
        if not settings.redis_url:
            return None
        return redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    except Exception:  # noqa: BLE001
        logger.debug("Redis unavailable for feature flags, falling back to DB")
        return None


def _coerce_cached_json(raw_value: object) -> str | bytes | bytearray | None:
    if isinstance(raw_value, (str, bytes, bytearray)):
        return raw_value
    return None


def _cache_key(tenant_id: UUID, flag_key: str) -> str:
    return f"ff:{tenant_id}:{flag_key}"


def _all_cache_key(tenant_id: UUID, role: str | None) -> str:
    return f"ff_all:{tenant_id}:{role or '_'}"


class FeatureFlagService:
    """Evaluate feature flags with Redis caching and DB fallback.
    
    Hybrid sync/async service:
    - For tests and legacy code: use is_enabled()/evaluate_all() with db parameter
    - For production: use is_enabled_async()/evaluate_all_async()
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._redis = _get_redis()
        self._legacy_mode = db is not None

    # ------------------------------------------------------------------
    # Public Sync API (legacy/test)
    # ------------------------------------------------------------------

    def is_enabled(
        self, flag_key: str, tenant_id: UUID, role: str | None = None
    ) -> bool:
        """Evaluate a single flag. Returns False if the flag does not exist.
        
        Legacy sync method for tests. Production code should use is_enabled_async().
        """
        if not self._legacy_mode:
            raise RuntimeError(
                "is_enabled() requires db to be set (legacy mode). "
                "Use is_enabled_async() for production."
            )

        # Try Redis cache first
        if self._redis:
            try:
                cached = _coerce_cached_json(self._redis.get(_cache_key(tenant_id, flag_key)))
                if cached is not None:
                    return self._evaluate_cached(json.loads(cached), tenant_id, role)
            except Exception:  # noqa: BLE001
                logger.debug("Redis read failed for flag %s", flag_key)

        # DB lookup: tenant-specific flag, then global fallback
        flag = (
            self.db.query(FeatureFlag)
            .filter(
                FeatureFlag.flag_key == flag_key,
                or_(
                    FeatureFlag.tenant_id == tenant_id,
                    FeatureFlag.tenant_id.is_(None),
                ),
            )
            .order_by(FeatureFlag.tenant_id.desc())  # tenant-specific first
            .first()
        )

        if flag is None:
            return False

        self._cache_flag(flag, tenant_id)
        return self._evaluate(flag, tenant_id, role)

    def evaluate_all(
        self, tenant_id: UUID, role: str | None = None
    ) -> dict[str, bool]:
        """Return a dict of all flags evaluated for the given context.
        
        Legacy sync method for tests. Production code should use evaluate_all_async().
        """
        if not self._legacy_mode:
            raise RuntimeError(
                "evaluate_all() requires db to be set (legacy mode). "
                "Use evaluate_all_async() for production."
            )

        cache_key = _all_cache_key(tenant_id, role)
        if self._redis:
            try:
                cached = _coerce_cached_json(self._redis.get(cache_key))
                if cached is not None:
                    loaded = json.loads(cached)
                    if isinstance(loaded, dict):
                        return {str(key): bool(value) for key, value in loaded.items()}
            except Exception:  # noqa: BLE001
                logger.debug("Redis read failed for evaluate_all")

        flags = (
            self.db.query(FeatureFlag)
            .filter(
                or_(
                    FeatureFlag.tenant_id == tenant_id,
                    FeatureFlag.tenant_id.is_(None),
                )
            )
            .all()
        )

        # Group by flag_key; tenant-specific overrides global
        by_key: dict[str, FeatureFlag] = {}
        for f in flags:
            if f.flag_key not in by_key or f.tenant_id is not None:
                by_key[f.flag_key] = f

        result = {key: self._evaluate(flag, tenant_id, role) for key, flag in by_key.items()}

        if self._redis:
            try:
                self._redis.setex(cache_key, _CACHE_TTL, json.dumps(result))
            except Exception:  # noqa: BLE001
                logger.debug("Redis write failed for evaluate_all cache")

        return result

    # ------------------------------------------------------------------
    # Public Async API (production)
    # ------------------------------------------------------------------

    async def is_enabled_async(
        self, flag_key: str, tenant_id: UUID, role: str | None = None
    ) -> bool:
        """Evaluate a single flag asynchronously using psycopg3.
        
        Production method. Returns False if the flag does not exist.
        """
        # Try Redis cache first
        if self._redis:
            try:
                cached = _coerce_cached_json(self._redis.get(_cache_key(tenant_id, flag_key)))
                if cached is not None:
                    return self._evaluate_cached(json.loads(cached), tenant_id, role)
            except Exception:  # noqa: BLE001
                logger.debug("Redis read failed for flag %s", flag_key)

        # DB lookup via psycopg3
        async with acquire() as conn:
            flag_row = await ff_queries.get_flag(
                conn, flag_key=flag_key, tenant_id=tenant_id
            )

        if flag_row is None:
            return False

        # Cache the flag
        if self._redis:
            try:
                payload = {
                    "flag_key": flag_row["flag_key"],
                    "enabled": flag_row["enabled"],
                    "config": flag_row["config"],
                }
                self._redis.setex(
                    _cache_key(tenant_id, flag_row["flag_key"]),
                    _CACHE_TTL,
                    json.dumps(payload),
                )
            except Exception:  # noqa: BLE001
                logger.debug("Redis write failed for flag %s", flag_key)

        return self._evaluate_from_row(flag_row, tenant_id, role)

    async def evaluate_all_async(
        self, tenant_id: UUID, role: str | None = None
    ) -> dict[str, bool]:
        """Return a dict of all flags evaluated for the given context asynchronously.
        
        Production method using psycopg3.
        """
        cache_key = _all_cache_key(tenant_id, role)
        if self._redis:
            try:
                cached = _coerce_cached_json(self._redis.get(cache_key))
                if cached is not None:
                    loaded = json.loads(cached)
                    if isinstance(loaded, dict):
                        return {str(key): bool(value) for key, value in loaded.items()}
            except Exception:  # noqa: BLE001
                logger.debug("Redis read failed for evaluate_all")

        # Fetch all flags via psycopg3
        async with acquire() as conn:
            flags = await ff_queries.list_all_tenant_flags(
                conn, tenant_id=tenant_id
            )

        # Group by flag_key; tenant-specific overrides global
        by_key: dict[str, dict[str, Any]] = {}
        for f in flags:
            if f["flag_key"] not in by_key or f["tenant_id"] is not None:
                by_key[f["flag_key"]] = f

        result = {
            key: self._evaluate_from_row(flag, tenant_id, role)
            for key, flag in by_key.items()
        }

        if self._redis:
            try:
                self._redis.setex(cache_key, _CACHE_TTL, json.dumps(result))
            except Exception:  # noqa: BLE001
                logger.debug("Redis write failed for evaluate_all cache")

        return result

    # ------------------------------------------------------------------
    # Evaluation logic
    # ------------------------------------------------------------------

    def _evaluate(self, flag: FeatureFlag, tenant_id: UUID, role: str | None) -> bool:
        """Evaluate a flag from SQLAlchemy ORM object.
        
        Priority:
        1. Role overrides (if applied, take precedence over enabled status)
        2. Enabled flag status
        3. Percentage rollout
        4. Return True if all pass
        """
        config = cast(Mapping[str, Any], flag.config or {})

        # Role overrides take precedence
        role_overrides = cast(dict[str, bool], config.get("role_overrides", {}))
        if role and role in role_overrides:
            return role_overrides[role]

        # Check enabled status
        if not flag.enabled:
            return False

        # Percentage rollout via consistent hashing
        pct = int(config.get("percentage_rollout", 100))
        if pct < 100:
            return self._in_rollout(tenant_id, flag.flag_key, pct)

        return True

    def _evaluate_from_row(
        self, flag_row: dict[str, Any], tenant_id: UUID, role: str | None
    ) -> bool:
        """Evaluate a flag from psycopg3 cursor row (dict).
        
        Priority:
        1. Role overrides (if applied, take precedence over enabled status)
        2. Enabled flag status
        3. Percentage rollout
        4. Return True if all pass
        """
        config = cast(Mapping[str, Any], flag_row.get("config") or {})

        # Role overrides take precedence
        role_overrides = cast(dict[str, bool], config.get("role_overrides", {}))
        if role and role in role_overrides:
            return role_overrides[role]

        # Check enabled status
        if not flag_row.get("enabled", False):
            return False

        # Percentage rollout via consistent hashing
        pct = int(config.get("percentage_rollout", 100))
        if pct < 100:
            return self._in_rollout(tenant_id, flag_row.get("flag_key", ""), pct)

        return True

    def _evaluate_cached(self, data: dict, tenant_id: UUID, role: str | None) -> bool:
        """Evaluate from cached JSON representation.
        
        Priority:
        1. Role overrides (if applied, take precedence over enabled status)
        2. Enabled flag status
        3. Percentage rollout
        4. Return True if all pass
        """
        config = cast(Mapping[str, Any], data.get("config") or {})

        # Role overrides take precedence
        role_overrides = cast(dict[str, bool], config.get("role_overrides", {}))
        if role and role in role_overrides:
            return role_overrides[role]

        # Check enabled status
        if not data.get("enabled", False):
            return False

        # Percentage rollout via consistent hashing
        pct = int(config.get("percentage_rollout", 100))
        if pct < 100:
            return self._in_rollout(tenant_id, data.get("flag_key", ""), pct)

        return True

    @staticmethod
    def _in_rollout(tenant_id: UUID, flag_key: str, percentage: int) -> bool:
        """Deterministic percentage rollout via consistent hashing."""
        digest = hashlib.sha256(f"{tenant_id}:{flag_key}".encode()).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < percentage

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_flag(self, flag: FeatureFlag, tenant_id: UUID) -> None:
        """Cache a single flag in Redis."""
        if not self._redis:
            return
        try:
            payload = {
                "flag_key": flag.flag_key,
                "enabled": flag.enabled,
                "config": flag.config,
            }
            self._redis.setex(
                _cache_key(tenant_id, flag.flag_key),
                _CACHE_TTL,
                json.dumps(payload),
            )
        except Exception:  # noqa: BLE001
            logger.debug("Redis write failed for flag %s", flag.flag_key)
