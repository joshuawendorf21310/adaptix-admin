"""Shared governance mixins for Phase 2 trust, replay, and evidence lineage."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Uuid as UUID


class EvidencePackReferenceMixin:
    """Reusable evidence and proof references for governed records."""

    evidence_pack_id = Column(String(255), nullable=True, index=True)
    evidence_refs = Column(JSON, nullable=True)
    proof_refs = Column(JSON, nullable=True)


class RetentionGovernanceMixin:
    """Reusable legal-hold and retention fields for governed records."""

    legal_hold = Column(Boolean, nullable=False, default=False, index=True)
    retention_expires_at = Column(DateTime, nullable=True, index=True)


class ReplayGovernanceMixin:
    """Reusable replay lineage fields for inbound integration events."""

    replay_state = Column(String(50), nullable=False, default="none", index=True)
    replay_of_event_id = Column(UUID(), nullable=True, index=True)
    replay_lineage = Column(JSON, nullable=True)
    replay_count = Column(Integer, nullable=False, default=0)
    replay_requested_at = Column(DateTime, nullable=True)
    last_replayed_at = Column(DateTime, nullable=True)
    replay_reason = Column(Text, nullable=True)


class TimelineGovernanceMixin:
    """Reusable cross-entity timeline lineage fields."""

    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(255), nullable=True, index=True)
    audit_log_id = Column(UUID(), nullable=True, index=True)
    blocker_id = Column(String(255), nullable=True, index=True)
    release_lineage = Column(JSON, nullable=True)
