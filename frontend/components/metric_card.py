"""Metric card component — label + large value + optional delta."""

from __future__ import annotations


def render_metric_card(label: str, value: str | int | float, delta: str | None = None, color: str | None = None) -> str:
    """Render a single metric card."""
    delta_html = ""
    if delta is not None:
        cls = "positive" if delta.startswith("+") else "negative" if delta.startswith("-") else ""
        delta_html = f'<div class="mc-delta {cls}">{delta}</div>'

    style = f' style="border-left: 3px solid {color}"' if color else ""

    return (
        f'<div class="metric-card"{style}>'
        f'<div class="mc-label">{label}</div>'
        f'<div class="mc-value">{value}</div>'
        f"{delta_html}"
        f"</div>"
    )


def render_metric_grid(metrics: list[dict]) -> str:
    """Render multiple metric cards in a grid.

    Each dict: {label, value, delta?, color?}
    """
    cards = [render_metric_card(**m) for m in metrics]
    return f'<div class="metric-grid">{"".join(cards)}</div>'
