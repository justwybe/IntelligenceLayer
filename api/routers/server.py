"""Inference server status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from api.deps import get_server_manager
from api.schemas.projects import ServerInfo

router = APIRouter(prefix="/api", tags=["server"], dependencies=[Depends(require_auth)])


@router.get("/server", response_model=ServerInfo)
async def server_status(server_manager=Depends(get_server_manager)) -> ServerInfo:
    info = server_manager.server_info()
    return ServerInfo(**info)
