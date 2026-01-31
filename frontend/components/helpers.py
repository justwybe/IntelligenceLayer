"""Helper utilities for HTML components."""

from __future__ import annotations

from datetime import datetime


def time_ago(timestamp: str) -> str:
    """Convert an ISO timestamp string to a relative time string."""
    if not timestamp:
        return ""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt
        seconds = int(diff.total_seconds())

        if seconds < 0:
            return "just now"
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            mins = seconds // 60
            return f"{mins}m ago"
        if seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        days = seconds // 86400
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days}d ago"
        return timestamp[:10]
    except (ValueError, TypeError):
        return timestamp[:16] if len(timestamp) > 16 else timestamp


def format_number(n: int | float) -> str:
    """Format a number with comma separators."""
    if isinstance(n, float):
        if n == int(n):
            return f"{int(n):,}"
        return f"{n:,.2f}"
    return f"{n:,}"


def truncate_path(path: str, max_len: int = 40) -> str:
    """Truncate a file path for display, keeping the tail."""
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3):]


def html_escape(text: str) -> str:
    """Basic HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
