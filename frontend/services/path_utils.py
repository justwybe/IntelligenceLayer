"""Path validation utilities for user-supplied file paths."""

from __future__ import annotations

import os
from pathlib import Path

_allowed_roots: list[str] = []


def init_allowed_roots(project_root: str) -> None:
    """Initialize the set of allowed root directories.

    Called once at app startup. Paths are resolved to absolute form.
    """
    global _allowed_roots
    data_dir = os.environ.get("WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio"))
    home = os.path.expanduser("~")
    _allowed_roots = [
        str(Path(project_root).resolve()),
        str(Path(data_dir).resolve()),
        str(Path(home).resolve()),
    ]


def validate_path(path: str, must_exist: bool = False) -> str | None:
    """Validate that a user-supplied path is within allowed roots.

    Returns an error message string if invalid, or None if the path is OK.
    """
    if not path or not path.strip():
        return "Path is required."

    try:
        resolved = str(Path(path).resolve())
    except (OSError, ValueError) as exc:
        return f"Invalid path: {exc}"

    if not _allowed_roots:
        # Not initialized — allow all (dev mode)
        pass
    else:
        if not any(resolved.startswith(root) for root in _allowed_roots):
            return f"Path is outside allowed directories: {path}"

    if must_exist and not Path(resolved).exists():
        return f"Path does not exist: {path}"

    return None
