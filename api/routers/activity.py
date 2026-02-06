"""Activity log endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.auth import require_auth
from api.deps import get_store
from api.schemas.projects import ActivityEntry, ActivityList

router = APIRouter(prefix="/api", tags=["activity"], dependencies=[Depends(require_auth)])


@router.get("/activity", response_model=ActivityList)
async def recent_activity(
    project_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    store=Depends(get_store),
) -> ActivityList:
    entries = store.recent_activity(project_id=project_id, limit=limit)
    return ActivityList(entries=[ActivityEntry(**e) for e in entries])
