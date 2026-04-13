"""AI policy models for production-grade governance."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AIPolicyRuleType(str, Enum):
    """AI policy rule types."""
    MODEL_ALLOWLIST = "model_allowlist"
    MODEL_DENYLIST = "model_denylist"
    OUTPUT_SAFETY = "output_safety"
    REDACTION = "redaction"
    RETENTION = "retention"
    PROMPT_LOGGING = "prompt_logging"
    PROVENANCE = "provenance"
    HUMAN_REVIEW = "human_review"
    ESCALATION = "escalation"


class AIPolicyStatus(str, Enum):
    """AI policy enforcement status."""
    DRAFT = "draft"
    DRY_RUN = "dry_run"
    ACTIVE = "active"
    DISABLED = "disabled"


class AIPolicyRule(BaseModel):
    """AI policy rule model."""
    id: str
    name: str
    rule_type: AIPolicyRuleType
    status: AIPolicyStatus = AIPolicyStatus.DRAFT
    description: str = ""

    # Rule configuration
    config: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)

    # Versioning
    version: int = 1
    previous_version_id: str | None = None

    # Metadata
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    last_simulated_at: datetime | None = None


class AIPolicyViolation(BaseModel):
    """AI policy violation audit event."""
    id: str
    policy_rule_id: str
    policy_rule_name: str
    violation_type: str
    severity: str
    tenant_id: str
    user_id: str
    model_used: str | None = None
    prompt_hash: str | None = None
    output_hash: str | None = None
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)
    remediated: bool = False
    remediated_by: str | None = None
    remediated_at: datetime | None = None


class AIModelConfig(BaseModel):
    """AI model configuration and allowlist."""
    model_id: str
    model_name: str
    provider: str
    allowed: bool = True
    requires_human_review: bool = False
    max_tokens: int | None = None
    temperature_limit: float | None = None
    redaction_required: bool = False
    retention_days: int | None = None
    tags: list[str] = Field(default_factory=list)
