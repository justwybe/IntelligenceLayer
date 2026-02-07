"""FastAPI dependency injection helpers.

All heavy services are stored on ``app.state`` during startup and retrieved
via these thin dependency functions.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from frontend.services.path_utils import validate_path


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


def get_project_root(request: Request) -> str:
    """Return the project root path."""
    return request.app.state.project_root


def get_soul_loop(request: Request):
    """Return the shared SoulLoop instance."""
    return request.app.state.soul_loop


def validate_path_param(path: str, *, must_exist: bool = False) -> str:
    """Validate a user-supplied path and return it, or raise 400."""
    error = validate_path(path, must_exist=must_exist)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return path
