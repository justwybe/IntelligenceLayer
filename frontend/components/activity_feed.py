"""Activity feed component — timeline with icons and timestamps."""

from __future__ import annotations

from frontend.components.helpers import time_ago
from frontend.constants import EVENT_COLORS, EVENT_ICONS


def render_activity_feed(events: list[dict], max_items: int = 15) -> str:
    """Render an activity feed timeline.

    Each event dict should have: event_type, message, created_at.
    """
    if not events:
        return (
            '<div style="color:var(--wybe-text-muted);padding:12px;font-size:13px">'
            "No recent activity</div>"
        )

    items = []
    for ev in events[:max_items]:
        event_type = ev.get("event_type", "")
        color = EVENT_COLORS.get(event_type, "#64748b")
        message = ev.get("message", "")
        created = ev.get("created_at", "")
        ago = time_ago(created) if created else ""

        items.append(
            f'<div class="activity-item">'
            f'<div class="activity-icon" style="background:{color}22;color:{color}">'
            f'<span style="font-size:10px">●</span>'
            f"</div>"
            f'<div class="activity-content">'
            f'<div class="activity-message">{message}</div>'
            f'<div class="activity-time">{ago}</div>'
            f"</div>"
            f"</div>"
        )

    return f'<div class="activity-feed">{"".join(items)}</div>'
