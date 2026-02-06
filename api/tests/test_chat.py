"""Tests for the chat endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_chat_returns_sse_stream(client):
    """POST /api/chat should return an SSE stream."""
    # Mock the agent to yield a simple text response
    mock_session = MagicMock()
    mock_session.session_id = "test-session-123"

    mock_agent = MagicMock()
    mock_agent.sessions.get_or_create.return_value = mock_session
    mock_agent.chat_stream.return_value = iter([
        {"type": "text", "content": "Hello!"},
    ])

    client.app.state.agent = mock_agent

    res = client.post("/api/chat", json={"message": "Hi"})
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    lines = res.text.strip().split("\n\n")
    # First event: session info
    assert '"type": "session"' in lines[0] or '"type":"session"' in lines[0]
    # Second event: text
    assert '"type": "text"' in lines[1] or '"type":"text"' in lines[1]
    # Last event: [DONE]
    assert lines[-1].strip() == "data: [DONE]"


def test_chat_agent_unavailable(client):
    """POST /api/chat should return 503 when agent is None."""
    client.app.state.agent = None

    res = client.post("/api/chat", json={"message": "Hi"})
    assert res.status_code == 503


def test_chat_with_tool_use(client):
    """POST /api/chat should stream tool_call and tool_result events."""
    mock_session = MagicMock()
    mock_session.session_id = "test-session-456"

    mock_agent = MagicMock()
    mock_agent.sessions.get_or_create.return_value = mock_session
    mock_agent.chat_stream.return_value = iter([
        {"type": "tool_call", "name": "list_projects", "input": {}},
        {"type": "tool_result", "name": "list_projects", "output": "[]", "is_error": False},
        {"type": "text", "content": "No projects found."},
    ])

    client.app.state.agent = mock_agent

    res = client.post("/api/chat", json={
        "message": "List projects",
        "session_id": "test-session-456",
        "project_id": "proj-1",
        "current_page": "training",
    })
    assert res.status_code == 200

    text = res.text
    assert "tool_call" in text
    assert "tool_result" in text
    assert "list_projects" in text


def test_chat_passes_context(client):
    """POST /api/chat should pass project_id and current_page to agent."""
    mock_session = MagicMock()
    mock_session.session_id = "ctx-session"

    mock_agent = MagicMock()
    mock_agent.sessions.get_or_create.return_value = mock_session
    mock_agent.chat_stream.return_value = iter([
        {"type": "text", "content": "ok"},
    ])

    client.app.state.agent = mock_agent

    client.post("/api/chat", json={
        "message": "help",
        "project_id": "proj-42",
        "current_page": "simulation",
    })

    mock_agent.chat_stream.assert_called_once_with(
        user_message="help",
        session=mock_session,
        project_id="proj-42",
        current_page="simulation",
    )
