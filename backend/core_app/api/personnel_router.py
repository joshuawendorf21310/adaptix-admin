"""Personnel router for the standalone Adaptix Admin shell.

This admin shell has no database layer installed. Personnel data is owned by
the core domain service and is not available here. All personnel endpoints
fail explicitly with a structured error so callers receive a truthful response
rather than a silent empty list.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/personnel", tags=["personnel"])


@router.get("/")
async def list_personnel(
    _current_user: CurrentUser = Depends(get_current_user),
) -> list[dict[str, str]]:
    """Return the list of personnel records.

    Raises a 503 Service Unavailable error because this standalone admin shell
    has no database layer and no connection to the core personnel data source.
    Personnel data must be fetched from the core domain service.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": "personnel_unavailable",
            "message": (
                "Personnel data is not available in this standalone admin shell. "
                "No database layer is configured and no connection to the core "
                "personnel service exists. Fetch personnel data from the core domain API."
            ),
        },
    )
