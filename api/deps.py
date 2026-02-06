"""FastAPI dependency injection helpers.

All heavy services are stored on ``app.state`` during startup and retrieved
via these thin dependency functions.
"""

from __future__ import annotations

from fastapi import Request


def get_store(request: Request):
    """Return the shared WorkspaceStore instance."""
    return request.app.state.store


def get_task_runner(request: Request):
    """Return the shared TaskRunner instance."""
    return request.app.state.task_runner


def get_server_manager(request: Request):
    """Return the shared ServerManager instance."""
    return request.app.state.server_manager


def get_agent(request: Request):
    """Return the shared WybeAgent instance."""
    return request.app.state.agent
