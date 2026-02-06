"""Pydantic models for the chat endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    project_id: str | None = None
    current_page: str | None = None
