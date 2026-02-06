"""GPU stats WebSocket endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from api.auth import verify_ws_token
from api.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared manager — the background broadcast task sends data here
gpu_manager = ConnectionManager()


@router.websocket("/ws/gpu")
async def gpu_ws(ws: WebSocket, token: str | None = Query(None)):
    """WebSocket endpoint for real-time GPU stats.

    Clients connect with ``?token=<api_key>``. A background task in
    ``main.py`` broadcasts GPU snapshots every N seconds.
    """
    if not verify_ws_token(token):
        await ws.close(code=4001, reason="Unauthorized")
        return

    await gpu_manager.connect(ws)
    try:
        # Keep connection alive — just wait for disconnect
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        gpu_manager.disconnect(ws)
