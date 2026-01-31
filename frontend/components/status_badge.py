"""Status badge component — colored pill with dot."""

from __future__ import annotations


def render_status_badge(status: str) -> str:
    """Render a status badge pill.

    Supported statuses: running, completed, failed, pending, stopped,
    imported, recorded, mimic, dreams.
    """
    normalised = status.lower().strip()

    badge_map = {
        "running": "badge-running",
        "completed": "badge-completed",
        "failed": "badge-failed",
        "pending": "badge-pending",
        "stopped": "badge-stopped",
        "imported": "badge-completed",
        "recorded": "badge-running",
        "mimic": "badge-pending",
        "dreams": "badge-pending",
    }
    css_cls = badge_map.get(normalised, "badge-pending")

    return (
        f'<span class="status-badge {css_cls}">'
        f'<span class="badge-dot"></span>'
        f"{normalised}"
        f"</span>"
    )
