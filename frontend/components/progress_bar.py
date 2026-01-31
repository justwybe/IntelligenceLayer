"""Progress bar component — styled fill bars with labels."""

from __future__ import annotations


def render_progress_bar(
    pct: float,
    label: str = "",
    sublabel: str = "",
    color: str = "var(--wybe-accent)",
) -> str:
    """Render a styled progress bar.

    Args:
        pct: Percentage (0-100).
        label: Left-side label text.
        sublabel: Right-side label text (e.g., "5,000 / 10,000 steps").
        color: CSS color for the fill.
    """
    pct = max(0, min(100, pct))

    return (
        f'<div class="progress-bar-container">'
        f'<div class="progress-bar-track">'
        f'<div class="progress-bar-fill" style="width:{pct:.1f}%;'
        f"background:linear-gradient(90deg, {color}, {color}dd)"
        f'"></div>'
        f"</div>"
        f'<div class="progress-bar-label">'
        f"<span>{label}</span>"
        f"<span>{sublabel}</span>"
        f"</div>"
        f"</div>"
    )
