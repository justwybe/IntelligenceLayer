"""Health check endpoint — unauthenticated."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from api.schemas.projects import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Return service health information."""
    from frontend.services.gpu_monitor import get_gpu_info

    gpus = get_gpu_info()
    start_time: float = getattr(request.app.state, "start_time", time.time())

    # Quick DB check
    db_ok = False
    try:
        store = request.app.state.store
        store.list_projects()
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        gpu_available=len(gpus) > 0,
        gpu_count=len(gpus),
        db_ok=db_ok,
        uptime_seconds=round(time.time() - start_time, 1),
    )
