from __future__ import annotations

from fastapi import APIRouter, Depends

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/prompts/audit")
async def ai_prompt_audit(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "total_prompts": 0,
        "active_prompts": 0,
        "guardrails_enabled": False,
        "pii_masking_enabled": False,
        "rate_limit_per_minute": 0,
        "prompts": [],
        "mode": "standalone-shell",
    }