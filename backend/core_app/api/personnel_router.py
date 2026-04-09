from __future__ import annotations

from fastapi import APIRouter, Depends

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/personnel", tags=["personnel"])


@router.get("/")
async def list_personnel(_current_user: CurrentUser = Depends(get_current_user)) -> list[dict[str, str]]:
    return []