"""Dataset card component — grid of dataset cards with metadata."""

from __future__ import annotations

from frontend.components.status_badge import render_status_badge


def render_dataset_card(dataset: dict) -> str:
    """Render a single dataset card."""
    name = dataset.get("name", "Unnamed")
    path = dataset.get("path", "")
    episodes = dataset.get("episode_count")
    source = dataset.get("source", "imported")
    created = dataset.get("created_at", "")
    if created and len(created) > 16:
        created = created[:16]

    ep_str = f"{episodes} episodes" if episodes else "Unknown episodes"

    return (
        f'<div class="dataset-card">'
        f'<div class="dc-name">{name}</div>'
        f'<div class="dc-meta">'
        f"<span>{ep_str}</span>"
        f"<span>{render_status_badge(source)}</span>"
        f"</div>"
        f'<div style="font-size:11px;color:var(--wybe-text-muted);'
        f'font-family:var(--wybe-font-mono);overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap" title="{path}">{path}</div>'
        f'<div style="font-size:11px;color:var(--wybe-text-muted);margin-top:4px">{created}</div>'
        f"</div>"
    )


def render_dataset_cards(datasets: list[dict]) -> str:
    """Render a grid of dataset cards."""
    if not datasets:
        return (
            '<div style="color:var(--wybe-text-muted);padding:20px;text-align:center">'
            "No datasets registered</div>"
        )
    cards = [render_dataset_card(ds) for ds in datasets]
    return f'<div class="card-grid">{"".join(cards)}</div>'
