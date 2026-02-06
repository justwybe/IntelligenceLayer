"""Streaming chat endpoint for the AI assistant."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.auth import require_auth
from api.deps import get_agent
from api.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"], dependencies=[Depends(require_auth)])


@router.post("/chat")
async def chat(body: ChatRequest, agent=Depends(get_agent)):
    """Stream assistant response as Server-Sent Events."""
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant unavailable — check ANTHROPIC_API_KEY",
        )

    session = agent.sessions.get_or_create(body.session_id)

    def event_stream():
        # First event: session_id so the client can persist it
        yield f"data: {json.dumps({'type': 'session', 'session_id': session.session_id})}\n\n"

        try:
            for chunk in agent.chat_stream(
                user_message=body.message,
                session=session,
                project_id=body.project_id,
                current_page=body.current_page or "datasets",
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception:
            logger.exception("chat_stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Internal error during streaming'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
