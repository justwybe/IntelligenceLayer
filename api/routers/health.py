"""Health check and system info endpoints — unauthenticated."""

from __future__ import annotations

import json
import os
import platform
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.schemas.projects import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


class SystemInfoResponse(BaseModel):
    platform: str
    python_version: str
    pytorch_version: str
    cuda_version: str
    transformers_version: str


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


@router.get("/health/monitor")
async def health_monitor() -> JSONResponse:
    """Return the latest health monitor status from health_status.json."""
    log_dir = os.environ.get("WYBE_LOG_DIR", "/tmp/intelligenceLayer_logs")
    status_file = os.path.join(log_dir, "health_status.json")
    try:
        with open(status_file) as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except (FileNotFoundError, json.JSONDecodeError):
        return JSONResponse(content={"status": "no monitor data"})


@router.get("/system-info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    """Return platform and library version strings."""
    pytorch_ver = "not installed"
    cuda_ver = "not available"
    try:
        import torch
        pytorch_ver = torch.__version__
        cuda_ver = torch.version.cuda or "not available"
    except ImportError:
        pass

    transformers_ver = "not installed"
    try:
        import transformers
        transformers_ver = transformers.__version__
    except ImportError:
        pass

    return SystemInfoResponse(
        platform=platform.platform(),
        python_version=platform.python_version(),
        pytorch_version=pytorch_ver,
        cuda_version=cuda_ver,
        transformers_version=transformers_ver,
    )
