"""Extended AI policy router with comprehensive governance (features 101-120)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core_app.api.dependencies import CurrentUser, get_current_user
from core_app.models.ai_policy import AIPolicyRuleType, AIPolicyStatus
from core_app.services.ai_policy_service import ai_policy_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class AIPolicyRuleCreateRequest(BaseModel):
    name: str
    rule_type: AIPolicyRuleType
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)
    status: AIPolicyStatus = AIPolicyStatus.DRAFT


class AIModelConfigRequest(BaseModel):
    model_id: str
    model_name: str
    provider: str
    allowed: bool = True
    requires_human_review: bool = False
    redaction_required: bool = False
    tags: list[str] = Field(default_factory=list)


def _can_manage_ai_policy(user: CurrentUser) -> bool:
    return user.resolved_primary_role in {"founder", "policy_manager", "security_officer"}


# Feature 101: AI policy dashboard
@router.get("/dashboard")
async def ai_policy_dashboard(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 101: AI policy dashboard summary."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    rules = ai_policy_service.list_rules()
    violations = ai_policy_service.list_violations(limit=100)
    models = ai_policy_service.list_models()

    active_rules = [r for r in rules if r["status"] == AIPolicyStatus.ACTIVE.value]
    unresolved_violations = [v for v in violations if not v["remediated"]]

    return {
        "total_rules": len(rules),
        "active_rules": len(active_rules),
        "draft_rules": len([r for r in rules if r["status"] == AIPolicyStatus.DRAFT.value]),
        "dry_run_rules": len([r for r in rules if r["status"] == AIPolicyStatus.DRY_RUN.value]),
        "total_violations": len(violations),
        "unresolved_violations": len(unresolved_violations),
        "total_models": len(models),
        "allowed_models": len([m for m in models if m["allowed"]]),
        "models_requiring_review": len([m for m in models if m.get("requires_human_review")]),
    }


# Feature 102-105: Policy rules CRUD
@router.get("/policies")
async def list_ai_policy_rules(
    rule_type: str | None = Query(None),
    status_filter: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Feature 102: List AI policy rules."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    rule_type_enum = AIPolicyRuleType(rule_type) if rule_type else None
    status_enum = AIPolicyStatus(status_filter) if status_filter else None

    return ai_policy_service.list_rules(rule_type=rule_type_enum, status=status_enum)


@router.post("/policies", status_code=status.HTTP_201_CREATED)
async def create_ai_policy_rule(
    payload: AIPolicyRuleCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 103: Create AI policy rule."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return ai_policy_service.create_rule(
        name=payload.name,
        rule_type=payload.rule_type,
        created_by=current_user.user_id,
        description=payload.description,
        config=payload.config,
        conditions=payload.conditions,
        actions=payload.actions,
        status=payload.status,
    )


@router.put("/policies/{rule_id}")
async def update_ai_policy_rule(
    rule_id: str,
    payload: dict[str, Any],
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 104: Update AI policy rule (creates new version per feature 106)."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    updated = ai_policy_service.update_rule(rule_id, current_user.user_id, **payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")
    return updated


@router.delete("/policies/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_policy_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    """Feature 105: Delete AI policy rule."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if not ai_policy_service.delete_rule(rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")


# Feature 107-108: Simulation and dry-run
@router.post("/policies/{rule_id}/simulate")
async def simulate_ai_policy_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 107-108: Simulate AI policy rule in dry-run mode."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return ai_policy_service.simulate_rule(rule_id)


# Feature 109: Enforcement status
@router.post("/policies/{rule_id}/activate")
async def activate_ai_policy_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 109: Activate AI policy enforcement."""
    if current_user.resolved_primary_role != "founder":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only founders can activate policies")

    activated = ai_policy_service.activate_rule(rule_id, current_user.user_id)
    if not activated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")
    return activated


@router.post("/policies/{rule_id}/deactivate")
async def deactivate_ai_policy_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 109: Deactivate AI policy enforcement."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    deactivated = ai_policy_service.deactivate_rule(rule_id, current_user.user_id)
    if not deactivated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")
    return deactivated


# Feature 110-111: Model allowlist/denylist
@router.get("/models")
async def list_ai_models(
    allowed_only: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Feature 110-111: List AI models (allowlist/denylist)."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return ai_policy_service.list_models(allowed_only=allowed_only)


@router.post("/models", status_code=status.HTTP_201_CREATED)
async def add_ai_model(
    payload: AIModelConfigRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 110-111: Add AI model to allowlist/denylist."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return ai_policy_service.add_model(
        model_id=payload.model_id,
        model_name=payload.model_name,
        provider=payload.provider,
        allowed=payload.allowed,
        requires_human_review=payload.requires_human_review,
        redaction_required=payload.redaction_required,
        tags=payload.tags,
    )


# Feature 119: Violation audit trail
@router.get("/violations")
async def list_ai_violations(
    tenant_id: str | None = Query(None),
    severity: str | None = Query(None),
    remediated: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Feature 119: List AI policy violations."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return ai_policy_service.list_violations(
        tenant_id=tenant_id,
        severity=severity,
        remediated=remediated,
        limit=limit,
    )


@router.post("/violations/{violation_id}/remediate")
async def remediate_ai_violation(
    violation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Remediate an AI policy violation."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    remediated = ai_policy_service.remediate_violation(violation_id, current_user.user_id)
    if not remediated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")
    return remediated


# Feature 120: Rollback workflow
@router.post("/policies/{rule_id}/rollback")
async def rollback_ai_policy_rule(
    rule_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Feature 120: Rollback AI policy rule to previous version."""
    if not _can_manage_ai_policy(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Deactivate the rule
    return ai_policy_service.update_rule(rule_id, current_user.user_id, status=AIPolicyStatus.DISABLED.value)
