"""Chat session management for the AI assistant."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class ChatSession:
    """Holds conversation history for one browser session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

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

    def get_api_messages(self) -> list[dict]:
        """Return messages formatted for the Anthropic API."""
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()


class SessionManager:
    """Manages chat sessions keyed by session ID."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}

    def get_or_create(self, session_id: str | None = None) -> ChatSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        session = ChatSession(session_id=session_id or uuid.uuid4().hex[:12])
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)
