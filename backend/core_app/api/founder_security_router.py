"""Founder security dashboard router (features 91-100)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from core_app.api.dependencies import CurrentUser, get_current_user
from core_app.services.ai_policy_service import ai_policy_service
from core_app.services.audit_service import audit_service
from core_app.services.feature_flag_service import feature_flag_service
from core_app.services.personnel_service import personnel_service

router = APIRouter(prefix="/api/v1/founder/security", tags=["founder-security"])


def _is_founder(user: CurrentUser) -> bool:
    return user.resolved_primary_role == "founder"


# Feature 91: Founder security dashboard
@router.get("/dashboard")
async def security_dashboard(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 91: Comprehensive founder security dashboard."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    # Gather data from all services
    all_accounts = personnel_service.list_accounts()
    privileged_accounts = personnel_service.get_privileged_accounts()
    inactive_accounts = personnel_service.get_inactive_accounts(days_threshold=90)

    flags = feature_flag_service.list_flags()
    stale_flags = feature_flag_service.get_stale_flags(days_threshold=90)

    legal_holds = audit_service.list_legal_holds()

    ai_violations = ai_policy_service.list_violations(limit=100)
    unresolved_ai_violations = [v for v in ai_violations if not v["remediated"]]

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "security_posture": {
            "status": "operational",
            "mode": "standalone-shell",
            "risks": len(stale_flags) + len(inactive_accounts) + len(unresolved_ai_violations),
        },
        "auth_summary": {
            "total_accounts": len(all_accounts),
            "active_accounts": len([a for a in all_accounts if a["is_active"]]),
            "privileged_accounts": len(privileged_accounts),
            "inactive_accounts": len(inactive_accounts),
        },
        "feature_flag_summary": {
            "total_flags": len(flags),
            "enabled_flags": len([f for f in flags if f.get("enabled")]),
            "stale_flags": len(stale_flags),
            "kill_switches": len([f for f in flags if f.get("is_kill_switch")]),
        },
        "audit_summary": {
            "mode": "standalone-shell",
            "upstream_connected": False,
        },
        "legal_hold_summary": {
            "total_holds": legal_holds["total"],
            "active_holds": len([h for h in legal_holds["items"] if h["status"] == "active"]),
        },
        "ai_policy_summary": {
            "total_violations": len(ai_violations),
            "unresolved_violations": len(unresolved_ai_violations),
        },
    }


# Feature 92: Security posture summary
@router.get("/posture")
async def security_posture(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 92: Security posture summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    return {
        "overall_status": "operational",
        "mode": "standalone-shell",
        "last_updated": datetime.now(UTC).isoformat(),
        "findings": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        },
        "recommendations": [
            "Connect upstream audit evidence source for full audit trail",
            "Review stale feature flags",
            "Complete access recertification",
        ],
    }


# Feature 93: Auth configuration summary
@router.get("/auth-config")
async def auth_configuration_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 93: Auth configuration summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    return {
        "dev_auth_enabled": True,
        "production_auth_ready": False,
        "bearer_token_validation": True,
        "role_based_access": True,
        "supported_roles": [
            "founder",
            "agency_admin",
            "compliance_officer",
            "security_officer",
            "policy_manager",
            "legal_hold_operator",
            "viewer",
        ],
    }


# Feature 94: Feature flag risk summary
@router.get("/feature-flag-risks")
async def feature_flag_risk_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 94: Feature flag risk summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    flags = feature_flag_service.list_flags()
    stale_flags = feature_flag_service.get_stale_flags(days_threshold=90)

    unapproved_flags = [f for f in flags if f.get("requires_approval") and not f.get("approved_by")]
    kill_switches = [f for f in flags if f.get("is_kill_switch")]

    return {
        "total_flags": len(flags),
        "stale_flags": len(stale_flags),
        "unapproved_flags": len(unapproved_flags),
        "kill_switches": len(kill_switches),
        "flags_with_dependencies": len([f for f in flags if f.get("dependencies")]),
        "risk_level": "low" if len(stale_flags) < 5 else "medium",
    }


# Feature 95: Audit evidence summary
@router.get("/audit-evidence")
async def audit_evidence_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 95: Audit evidence summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    return {
        "mode": "standalone-shell",
        "upstream_connected": False,
        "local_admin_events": 0,
        "message": "No upstream audit evidence source connected. Connect for full audit trail.",
    }


# Feature 96: Legal hold summary
@router.get("/legal-holds")
async def legal_hold_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 96: Legal hold summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    holds = audit_service.list_legal_holds()
    active_holds = [h for h in holds["items"] if h["status"] == "active"]

    return {
        "total_holds": holds["total"],
        "active_holds": len(active_holds),
        "released_holds": len([h for h in holds["items"] if h["status"] == "released"]),
    }


# Feature 97: Policy exception summary
@router.get("/policy-exceptions")
async def policy_exception_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 97: Policy exception summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    return {
        "total_exceptions": 0,
        "active_exceptions": 0,
        "expired_exceptions": 0,
        "message": "Policy exception tracking ready for configuration",
    }


# Feature 98: Privileged user summary
@router.get("/privileged-users")
async def privileged_user_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 98: Privileged user summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    privileged = personnel_service.get_privileged_accounts()

    return {
        "total_privileged": len(privileged),
        "founders": len([p for p in privileged if p["primary_role"] == "founder"]),
        "agency_admins": len([p for p in privileged if p["primary_role"] == "agency_admin"]),
        "security_officers": len([p for p in privileged if p["primary_role"] == "security_officer"]),
    }


# Feature 99: Stale session summary
@router.get("/stale-sessions")
async def stale_session_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 99: Stale session summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    inactive = personnel_service.get_inactive_accounts(days_threshold=90)

    return {
        "inactive_accounts_90_days": len(inactive),
        "message": "Session tracking enhanced with account activity monitoring",
    }


# Feature 100: Suspicious auth summary
@router.get("/suspicious-auth")
async def suspicious_auth_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    """Feature 100: Suspicious auth summary."""
    if not _is_founder(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Founder access only")

    return {
        "suspicious_events": 0,
        "blocked_attempts": 0,
        "mode": "standalone-shell",
        "message": "Suspicious auth detection ready. Connect upstream security monitoring for real-time detection.",
    }
