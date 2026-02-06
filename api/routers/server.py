"""Inference server status, deploy, and stop endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from api.deps import get_server_manager
from api.schemas.models import DeployRequest, DeployResponse
from api.schemas.projects import ServerInfo

router = APIRouter(prefix="/api", tags=["server"], dependencies=[Depends(require_auth)])


@router.get("/server", response_model=ServerInfo)
async def server_status(server_manager=Depends(get_server_manager)) -> ServerInfo:
    info = server_manager.server_info()
    return ServerInfo(**info)


@router.post("/server/deploy", response_model=DeployResponse)
async def deploy_server(
    body: DeployRequest,
    server_manager=Depends(get_server_manager),
) -> DeployResponse:
    msg = server_manager.start(
        model_path=body.model_path,
        embodiment_tag=body.embodiment_tag,
        port=body.port,
    )
    status = server_manager.status()
    return DeployResponse(message=msg, status=status)


@router.post("/server/stop", response_model=DeployResponse)
async def stop_server(
    server_manager=Depends(get_server_manager),
) -> DeployResponse:
    msg = server_manager.stop()
    status = server_manager.status()
    return DeployResponse(message=msg, status=status)
