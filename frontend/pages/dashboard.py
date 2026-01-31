"""Dashboard sidebar — GPU status, server status, metrics, activity feed."""

from __future__ import annotations

import platform
from typing import Any

import gradio as gr

from frontend.components.activity_feed import render_activity_feed
from frontend.components.gpu_panel import render_gpu_cards
from frontend.components.metric_card import render_metric_grid
from frontend.services.gpu_monitor import get_gpu_info
from frontend.services.workspace import WorkspaceStore


def _system_info() -> str:
    lines = [f"- **Platform**: {platform.system()} {platform.release()}"]
    try:
        import torch
        lines.append(f"- **PyTorch**: {torch.__version__}")
        lines.append(f"- **CUDA available**: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            lines.append(f"- **CUDA version**: {torch.version.cuda}")
    except ImportError:
        lines.append("- **PyTorch**: not installed")
    try:
        import transformers
        lines.append(f"- **Transformers**: {transformers.__version__}")
    except ImportError:
        pass
    return "\n".join(lines)


def _get_summary_metrics(store: WorkspaceStore, project_id: str | None) -> str:
    datasets = store.list_datasets(project_id=project_id)
    models = store.list_models(project_id=project_id)
    runs = store.list_runs(project_id=project_id)
    active = [r for r in runs if r["status"] in ("running", "pending")]

    metrics = [
        {"label": "Datasets", "value": len(datasets), "color": "#a855f7"},
        {"label": "Models", "value": len(models), "color": "#06b6d4"},
        {"label": "Total Runs", "value": len(runs), "color": "#3b82f6"},
        {"label": "Active Runs", "value": len(active), "color": "#22c55e"},
    ]
    return render_metric_grid(metrics)


def _get_server_status_html(server_manager: Any) -> str:
    try:
        status = server_manager.status()
        if status == "running":
            alive = server_manager.ping()
            dot_class = "alive" if alive else "starting"
            label = "Running" if alive else "Starting..."
            model = server_manager.current_model_path or "unknown"
            port = server_manager.current_port
            return (
                f'<div style="display:flex;align-items:center;gap:8px">'
                f'<span class="health-dot {dot_class}"></span>'
                f'<span style="color:var(--wybe-text);font-size:13px">'
                f"Server {label} — port {port}</span></div>"
                f'<div style="font-size:11px;color:var(--wybe-text-muted);margin-top:4px">'
                f"Model: {model}</div>"
            )
        return (
            '<div style="display:flex;align-items:center;gap:8px">'
            '<span class="health-dot dead"></span>'
            '<span style="color:var(--wybe-text-muted);font-size:13px">Server Stopped</span></div>'
        )
    except Exception:
        return '<span style="color:var(--wybe-text-muted)">Server status unavailable</span>'


def create_dashboard_sidebar(
    store: WorkspaceStore,
    server_manager: Any,
    project_state: gr.State,
) -> dict:
    """Create the dashboard sidebar overlay. Returns dict of components for timer updates."""

    with gr.Column(visible=False, elem_classes="sidebar-overlay") as sidebar:
        gr.HTML('<div class="section-title">Dashboard</div>')

        # Summary metrics
        summary_metrics = gr.HTML(value=_get_summary_metrics(store, None))

        # GPU Status
        gr.HTML('<div class="section-title">GPU Status</div>')
        gpu_html = gr.HTML(value=render_gpu_cards(get_gpu_info()))

        # Server status
        gr.HTML('<div class="section-title">Inference Server</div>')
        server_html = gr.HTML(value=_get_server_status_html(server_manager))

        # Activity feed
        gr.HTML('<div class="section-title">Recent Activity</div>')
        activity_html = gr.HTML(
            value=render_activity_feed(store.recent_activity(limit=15))
        )

        # System info
        with gr.Accordion("System Info", open=False):
            gr.Markdown(value=_system_info())

    # Callback functions for timer updates
    def refresh_gpu():
        return render_gpu_cards(get_gpu_info())

    def refresh_server():
        return _get_server_status_html(server_manager)

    def refresh_metrics(proj):
        pid = proj.get("id") if proj else None
        return _get_summary_metrics(store, pid)

    def refresh_activity(proj):
        pid = proj.get("id") if proj else None
        events = store.recent_activity(project_id=pid, limit=15)
        return render_activity_feed(events)

    return {
        "sidebar": sidebar,
        "gpu_html": gpu_html,
        "server_html": server_html,
        "summary_metrics": summary_metrics,
        "activity_html": activity_html,
        "refresh_gpu": refresh_gpu,
        "refresh_server": refresh_server,
        "refresh_metrics": refresh_metrics,
        "refresh_activity": refresh_activity,
    }
