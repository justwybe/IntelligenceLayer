"""Pipeline stepper component — horizontal status bar for navigation."""

from __future__ import annotations

from frontend.components.icons import (
    icon_bar_chart,
    icon_database,
    icon_brain,
    icon_rocket,
)

STAGES = [
    {"id": "datasets",    "label": "Datasets",    "icon_fn": icon_database},
    {"id": "training",    "label": "Training",    "icon_fn": icon_brain},
    {"id": "simulation",  "label": "Simulation",  "icon_fn": icon_bar_chart},
    {"id": "models",      "label": "Models",      "icon_fn": icon_rocket},
]


def render_pipeline_stepper(active_page: str = "datasets", stage_statuses: dict | None = None) -> str:
    """Render the horizontal pipeline stepper.

    Args:
        active_page: Currently active page ID.
        stage_statuses: Optional dict mapping stage id to status
            ("completed", "running", "pending").
    """
    statuses = stage_statuses or {}
    parts = []
    parts.append('<div class="pipeline-stepper">')

    for i, stage in enumerate(STAGES):
        css_classes = ["step-node"]
        if stage["id"] == active_page:
            css_classes.append("active")
        status = statuses.get(stage["id"], "")
        if status:
            css_classes.append(status)

        icon = stage["icon_fn"](14)
        parts.append(
            f'<div class="{" ".join(css_classes)}" data-page="{stage["id"]}">'
            f'<span class="step-dot"></span>'
            f'{icon}'
            f'<span>{stage["label"]}</span>'
            f'</div>'
        )

        if i < len(STAGES) - 1:
            conn_cls = "step-connector"
            # Mark connectors before completed stages
            next_status = statuses.get(STAGES[i + 1]["id"], "")
            if status == "completed" and next_status in ("completed", "running"):
                conn_cls += " done"
            parts.append(f'<div class="{conn_cls}"></div>')

    parts.append("</div>")
    return "\n".join(parts)
