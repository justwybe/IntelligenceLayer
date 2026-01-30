from __future__ import annotations

"""Workbench tab — GPU status, server controls, inference playground, activity feed.

Merges the old Dashboard and Inference tabs into a single unified workspace.
"""

import json
import platform
import subprocess
import traceback

import gradio as gr
import numpy as np

from frontend.services.gpu_monitor import format_gpu_markdown, get_gpu_info
from frontend.services.server_manager import ServerManager
from frontend.services.workspace import WorkspaceStore

EMBODIMENT_CHOICES = [
    "new_embodiment",
    "gr1",
    "unitree_g1",
    "libero_panda",
    "oxe_google",
    "oxe_widowx",
    "robocasa_panda_omron",
    "behavior_r1_pro",
]


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


def _server_badge(sm: ServerManager) -> str:
    running = sm.ping()
    if running:
        info = (
            f"**Model**: `{sm.current_model_path or 'unknown'}`\n\n"
            f"**Embodiment**: `{sm.current_embodiment_tag or 'unknown'}`\n\n"
            f"**Port**: `{sm.current_port}`"
        )
        return f"### Server Running\n\n{info}"
    proc_status = sm.status()
    if proc_status == "running":
        return "### Server Starting..."
    return "### Server Stopped"


def _format_activity(store: WorkspaceStore, project_id: str | None) -> str:
    events = store.recent_activity(project_id=project_id, limit=15)
    if not events:
        return "*No recent activity*"
    lines = []
    for ev in events:
        ts = ev["created_at"]
        if ts and len(ts) > 16:
            ts = ts[:16]
        lines.append(f"- `{ts}` {ev['message']}")
    return "\n".join(lines)


def create_workbench_tab(
    server_manager: ServerManager,
    store: WorkspaceStore,
    project_state: gr.State,
):
    with gr.Tab("Workbench"):
        gr.Markdown("## Workbench")

        with gr.Row():
            # ── Left panel: System status ──
            with gr.Column(scale=1):
                gr.Markdown("### System Status")
                gpu_display = gr.Markdown(
                    value=format_gpu_markdown(get_gpu_info()),
                )
                server_status = gr.Markdown(
                    value=_server_badge(server_manager),
                )

                gr.Markdown("---")
                gr.Markdown("### Server Controls")
                model_path_input = gr.Textbox(
                    label="Model Path",
                    placeholder="nvidia/GR00T-N1.6-3B or /path/to/checkpoint",
                    value="nvidia/GR00T-N1.6-3B",
                )
                with gr.Row():
                    embodiment_input = gr.Dropdown(
                        label="Embodiment Tag",
                        choices=EMBODIMENT_CHOICES,
                        value="new_embodiment",
                    )
                    port_input = gr.Number(
                        label="Port",
                        value=5555,
                        precision=0,
                    )
                with gr.Row():
                    start_btn = gr.Button("Start Server", variant="primary", size="sm")
                    stop_btn = gr.Button("Stop Server", variant="stop", size="sm")
                    health_btn = gr.Button("Health Check", size="sm")
                server_log = gr.Textbox(label="Server Output", lines=4, interactive=False)

                gr.Markdown("---")
                gr.Markdown("### Active Runs")
                active_runs_display = gr.Markdown(value="*No active runs*")

                gr.Markdown("---")
                gr.Markdown("### Recent Activity")
                activity_display = gr.Markdown(
                    value=_format_activity(store, None),
                )

                gr.Markdown("---")
                system_info = gr.Markdown(value=_system_info())

            # ── Right panel: Inference playground ──
            with gr.Column(scale=1):
                gr.Markdown("### Inference Playground")
                gr.Markdown("Send observations to the running server and view predicted actions.")

                language_input = gr.Textbox(
                    label="Language Command",
                    placeholder="Pick up the red cube and place it in the bowl",
                )
                with gr.Row():
                    image1 = gr.Image(label="Camera 1", type="numpy")
                    image2 = gr.Image(label="Camera 2 (opt)", type="numpy")
                    image3 = gr.Image(label="Camera 3 (opt)", type="numpy")

                modality_info = gr.Markdown(
                    "Click **Query Config** to see expected inputs."
                )
                with gr.Row():
                    query_config_btn = gr.Button("Query Config", size="sm")
                    send_btn = gr.Button("Send to Server", variant="primary", size="sm")

                state_input = gr.Code(
                    label="Robot State (JSON)",
                    language="json",
                    value='{\n  "x": [0.0],\n  "y": [0.0],\n  "z": [0.0]\n}',
                    lines=6,
                )
                action_output = gr.Code(
                    label="Action Output (JSON)",
                    language="json",
                    lines=12,
                    interactive=False,
                )
                action_plot = gr.Plot(label="Action Trajectory")
                inf_status_msg = gr.Textbox(label="Status", interactive=False)

        # ── Callbacks ──

        def start_server(model_path, embodiment_tag, port):
            msg = server_manager.start(model_path, embodiment_tag, port=int(port))
            return msg, _server_badge(server_manager)

        def stop_server():
            msg = server_manager.stop()
            return msg, _server_badge(server_manager)

        def health_check():
            alive = server_manager.ping()
            return "Health check: Server is responsive" if alive else "Health check: Server is NOT responding"

        def refresh_gpu():
            return format_gpu_markdown(get_gpu_info())

        def refresh_status():
            return _server_badge(server_manager)

        def refresh_log():
            return server_manager.tail_log(30)

        def refresh_active_runs():
            runs = store.get_active_runs()
            if not runs:
                return "*No active runs*"
            lines = []
            for r in runs[:10]:
                lines.append(f"- **{r['run_type']}** `{r['id'][:8]}` — {r['status']}")
            return "\n".join(lines)

        def refresh_activity(proj):
            pid = proj.get("id") if proj else None
            return _format_activity(store, pid)

        def query_modality_config():
            try:
                if not server_manager.ping():
                    return "Server is not running. Start the server first."
                import sys

                sys.path.insert(0, server_manager._project_root)
                from gr00t.policy.server_client import PolicyClient

                client = PolicyClient(
                    host="localhost", port=server_manager.current_port, timeout_ms=5000
                )
                config = client.get_modality_config()
                parts = []
                for modality_name, mc in config.items():
                    keys = mc.modality_keys if hasattr(mc, "modality_keys") else str(mc)
                    parts.append(f"**{modality_name}**: `{keys}`")
                return "\n\n".join(parts)
            except Exception as exc:
                return f"Error querying config: {exc}"

        def send_observation(img1, img2, img3, language, state_json):
            try:
                if not server_manager.ping():
                    return "{}", None, "Server is not running"

                import sys

                sys.path.insert(0, server_manager._project_root)
                from gr00t.policy.server_client import PolicyClient

                client = PolicyClient(
                    host="localhost", port=server_manager.current_port, timeout_ms=15000
                )

                observation = {"video": {}, "state": {}, "language": {}}
                images = [img for img in [img1, img2, img3] if img is not None]
                if not images:
                    return "{}", None, "At least one camera image is required"

                try:
                    config = client.get_modality_config()
                    video_keys = (
                        config["video"].modality_keys if "video" in config else []
                    )
                    lang_keys = (
                        config["language"].modality_keys
                        if "language" in config
                        else []
                    )
                except Exception:
                    video_keys = [f"camera_{i}" for i in range(len(images))]
                    lang_keys = ["annotation.human.task_description"]

                for i, img in enumerate(images):
                    key = video_keys[i] if i < len(video_keys) else f"camera_{i}"
                    observation["video"][key] = np.array(img)[None, :]

                lang_key = (
                    lang_keys[0] if lang_keys else "annotation.human.task_description"
                )
                observation["language"][lang_key] = [[language or ""]]

                try:
                    state_dict = json.loads(state_json) if state_json else {}
                except json.JSONDecodeError:
                    return "{}", None, "Invalid JSON in state input"

                for k, v in state_dict.items():
                    observation["state"][k] = np.array(v, dtype=np.float32)[None, :]

                action, info = client.get_action(observation)

                action_serializable = {}
                for k, v in action.items():
                    action_serializable[k] = v.tolist() if isinstance(v, np.ndarray) else v

                action_json = json.dumps(action_serializable, indent=2)
                fig = _plot_actions(action)
                return action_json, fig, "Inference successful"

            except Exception as exc:
                return "{}", None, f"Error: {exc}\n{traceback.format_exc()}"

        start_btn.click(
            start_server,
            inputs=[model_path_input, embodiment_input, port_input],
            outputs=[server_log, server_status],
        )
        stop_btn.click(stop_server, outputs=[server_log, server_status])
        health_btn.click(health_check, outputs=[server_log])

        query_config_btn.click(query_modality_config, outputs=[modality_info])
        send_btn.click(
            send_observation,
            inputs=[image1, image2, image3, language_input, state_input],
            outputs=[action_output, action_plot, inf_status_msg],
        )

        # Auto-refresh timers
        timer = gr.Timer(5)
        timer.tick(refresh_gpu, outputs=[gpu_display])
        timer.tick(refresh_status, outputs=[server_status])
        timer.tick(refresh_active_runs, outputs=[active_runs_display])
        timer.tick(refresh_activity, inputs=[project_state], outputs=[activity_display])


def _plot_actions(action: dict):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(
            len(action),
            1,
            figsize=(8, max(3 * len(action), 4)),
            squeeze=False,
        )
        for i, (key, values) in enumerate(action.items()):
            arr = np.array(values)
            if arr.ndim == 1:
                axes[i, 0].bar(range(len(arr)), arr)
            elif arr.ndim == 2:
                for dim in range(arr.shape[1]):
                    axes[i, 0].plot(arr[:, dim], label=f"dim {dim}")
                axes[i, 0].legend(fontsize=7)
            axes[i, 0].set_title(key, fontsize=9)
        plt.tight_layout()
        return fig
    except Exception:
        return None
