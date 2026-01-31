"""Toast notification component — slide-in alerts."""

from __future__ import annotations


def render_toast(message: str, toast_type: str = "info") -> str:
    """Render a toast notification.

    Args:
        message: Notification text.
        toast_type: One of "success", "error", "info".
    """
    css_cls = f"toast-{toast_type}" if toast_type in ("success", "error", "info") else "toast-info"
    return (
        f'<div class="toast {css_cls}">'
        f"{message}"
        f"</div>"
    )


def render_toast_container(toasts: list[dict]) -> str:
    """Render a toast container with multiple notifications.

    Each dict: {message, type}.
    """
    if not toasts:
        return ""
    toast_html = "".join(
        render_toast(t["message"], t.get("type", "info")) for t in toasts
    )
    return f'<div class="toast-container">{toast_html}</div>'
