"""Chat session management for the AI assistant."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


MAX_MESSAGES = 200
MAX_SESSIONS = 100
SESSION_TTL_SECONDS = 3600  # 1 hour


@dataclass
class ChatSession:
    """Holds conversation history for one browser session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)

    def _touch(self) -> None:
        """Update the last-active timestamp."""
        self.last_active = time.time()

    def _trim(self) -> None:
        """Keep only the last MAX_MESSAGES messages."""
        if len(self.messages) > MAX_MESSAGES:
            self.messages = self.messages[-MAX_MESSAGES:]

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self._touch()
        self._trim()

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})
        self._touch()
        self._trim()

    def add_tool_use(self, tool_use_id: str, tool_name: str, tool_input: dict) -> None:
        """Record a tool use block as part of the assistant's response."""
        self.messages.append({
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": tool_use_id,
                "name": tool_name,
                "input": tool_input,
            }],
        })
        self._touch()
        self._trim()

    def add_tool_result(self, tool_use_id: str, output: str, is_error: bool = False) -> None:
        """Record a tool result."""
        content: dict = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": output,
        }
        if is_error:
            content["is_error"] = True
        self.messages.append({"role": "user", "content": [content]})
        self._touch()
        self._trim()

    def get_api_messages(self) -> list[dict]:
        """Return messages formatted for the Anthropic API."""
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()


class SessionManager:
    """Manages chat sessions keyed by session ID."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}

    def _cleanup_expired(self) -> None:
        """Remove sessions that have been inactive for longer than SESSION_TTL_SECONDS."""
        now = time.time()
        expired = [
            sid for sid, session in self._sessions.items()
            if now - session.last_active > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]

    def _evict_oldest(self) -> None:
        """Evict the oldest session if we exceed MAX_SESSIONS."""
        if len(self._sessions) >= MAX_SESSIONS:
            oldest_sid = min(
                self._sessions, key=lambda sid: self._sessions[sid].last_active
            )
            del self._sessions[oldest_sid]

    def get_or_create(self, session_id: str | None = None) -> ChatSession:
        self._cleanup_expired()
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session._touch()
            return session
        self._evict_oldest()
        session = ChatSession(session_id=session_id or uuid.uuid4().hex[:12])
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)
