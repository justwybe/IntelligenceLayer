"""GPU information endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from api.schemas.projects import GPUInfo, GPUResponse

router = APIRouter(prefix="/api", tags=["gpu"], dependencies=[Depends(require_auth)])


@router.get("/gpu", response_model=GPUResponse)
async def gpu_info() -> GPUResponse:
    from frontend.services.gpu_monitor import get_gpu_info

    gpus = get_gpu_info()
    return GPUResponse(
        gpus=[GPUInfo(**g) for g in gpus],
        gpu_available=len(gpus) > 0,
        gpu_count=len(gpus),
    )
