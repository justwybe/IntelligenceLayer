"""Pydantic models for the Soul System API."""

from __future__ import annotations

from pydantic import BaseModel


class ResidentCreate(BaseModel):
    name: str
    room: str | None = None
    notes: str | None = None


class ResidentResponse(BaseModel):
    id: str
    name: str
    room: str | None = None
    notes: str | None = None


class ResidentList(BaseModel):
    residents: list[ResidentResponse]


class ConversationStart(BaseModel):
    resident_id: str | None = None


class ConversationStartResponse(BaseModel):
    conversation_id: str
    resident_id: str | None = None


class ConversationEnd(BaseModel):
    summary: str | None = None


class SoulChatRequest(BaseModel):
    message: str
    resident_id: str | None = None


class SoulChatResponse(BaseModel):
    response_text: str
    actions_executed: int
    actions_succeeded: int
    model_used: str
    intent: str
    think_time_ms: int
    act_time_ms: int
