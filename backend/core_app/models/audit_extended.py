"""Extended audit models for production-grade governance."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEventType(str, Enum):
    """Audit event type classification."""
    AUTH = "auth"
    FEATURE_FLAG = "feature_flag"
    ADMIN_ACTION = "admin_action"
    POLICY_CHANGE = "policy_change"
    DATA_ACCESS = "data_access"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class AuditEvent(BaseModel):
    """Comprehensive audit event model."""
    id: str
    event_type: AuditEventType
    action: str
    severity: AuditSeverity = AuditSeverity.INFO

    # Actor information
    actor_user_id: str
    actor_tenant_id: str
    actor_role: str

    # Resource information
    resource_type: str
    resource_id: str | None = None
    tenant_id: str | None = None
    domain: str | None = None

    # Event details
    description: str
    details: dict[str, Any] = Field(default_factory=dict)

    # Correlation & tracing
    correlation_id: str | None = None
    causation_id: str | None = None
    request_id: str | None = None

    # Metadata
    timestamp: datetime
    ip_address: str | None = None
    user_agent: str | None = None


class LegalHoldStatus(str, Enum):
    """Legal hold lifecycle status."""
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


class LegalHold(BaseModel):
    """Legal hold model for evidence preservation."""
    id: str
    case_id: str
    scope: str
    reason: str
    status: LegalHoldStatus = LegalHoldStatus.ACTIVE

    # Custodians
    custodian_user_ids: list[str] = Field(default_factory=list)
    custodian_tenant_ids: list[str] = Field(default_factory=list)

    # Timeline
    created_at: datetime
    created_by: str
    released_at: datetime | None = None
    released_by: str | None = None
    expires_at: datetime | None = None

    # Acknowledgment
    notice_sent_at: datetime | None = None
    acknowledged_by: list[str] = Field(default_factory=list)
    acknowledged_at: dict[str, datetime] = Field(default_factory=dict)

    # Evidence
    affected_event_count: int = 0
    evidence_packet_id: str | None = None


class ReplayRequest(BaseModel):
    """Audit event replay request model."""
    id: str
    webhook_id: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    reason: str
    requested_by: str
    requested_at: datetime
    status: str = "pending"
    dry_run: bool = False
    authorized_by: str | None = None
    authorized_at: datetime | None = None
    executed_at: datetime | None = None
    result: dict[str, Any] = Field(default_factory=dict)
