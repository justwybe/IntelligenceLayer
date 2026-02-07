"""Soul System API — chat with Wybe, manage residents and conversations."""

from __future__ import annotations

import asyncio
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import require_auth
from api.deps import get_soul_loop
from api.schemas.soul import (
    ConversationEnd,
    ConversationStart,
    ConversationStartResponse,
    ResidentCreate,
    ResidentList,
    ResidentResponse,
    SoulChatRequest,
    SoulChatResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/soul", tags=["soul"], dependencies=[Depends(require_auth)])

# SoulLoop has mutable instance state — serialize access to process_text()
_soul_lock = threading.Lock()


def _require_soul(soul_loop):
    if soul_loop is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Soul System unavailable — check ANTHROPIC_API_KEY",
        )
    return soul_loop


@router.get("/residents", response_model=ResidentList)
async def list_residents(soul_loop=Depends(get_soul_loop)):
    sl = _require_soul(soul_loop)
    residents = await asyncio.get_event_loop().run_in_executor(
        None, sl.residents.list_all
    )
    return ResidentList(
        residents=[ResidentResponse(id=r["id"], name=r["name"], room=r.get("room"), notes=r.get("notes")) for r in residents]
    )


@router.post("/residents", response_model=ResidentResponse, status_code=201)
async def create_resident(body: ResidentCreate, soul_loop=Depends(get_soul_loop)):
    sl = _require_soul(soul_loop)
    rid = await asyncio.get_event_loop().run_in_executor(
        None, lambda: sl.residents.create(name=body.name, room=body.room, notes=body.notes)
    )
    return ResidentResponse(id=rid, name=body.name, room=body.room, notes=body.notes)


@router.get("/residents/{resident_id}", response_model=ResidentResponse)
async def get_resident(resident_id: str, soul_loop=Depends(get_soul_loop)):
    sl = _require_soul(soul_loop)
    r = await asyncio.get_event_loop().run_in_executor(
        None, lambda: sl.residents.get(resident_id)
    )
    if not r:
        raise HTTPException(status_code=404, detail="Resident not found")
    return ResidentResponse(id=r["id"], name=r["name"], room=r.get("room"), notes=r.get("notes"))


@router.post("/conversations/start", response_model=ConversationStartResponse)
async def start_conversation(body: ConversationStart, soul_loop=Depends(get_soul_loop)):
    sl = _require_soul(soul_loop)
    cid = await asyncio.get_event_loop().run_in_executor(
        None, lambda: sl.start_conversation(resident_id=body.resident_id)
    )
    return ConversationStartResponse(conversation_id=cid, resident_id=body.resident_id)


@router.post("/conversations/end")
async def end_conversation(body: ConversationEnd, soul_loop=Depends(get_soul_loop)):
    sl = _require_soul(soul_loop)
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: sl.end_conversation(summary=body.summary)
    )
    return {"status": "ended"}


@router.post("/chat", response_model=SoulChatResponse)
async def soul_chat(body: SoulChatRequest, soul_loop=Depends(get_soul_loop)):
    sl = _require_soul(soul_loop)

    if body.resident_id:
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: sl.set_resident(body.resident_id)
        )

    def _process():
        with _soul_lock:
            return sl.process_text(body.message)

    result = await asyncio.get_event_loop().run_in_executor(None, _process)
    return SoulChatResponse(**result)
