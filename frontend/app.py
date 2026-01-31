"""Main entry point for Wybe Studio — the IntelligenceLayer frontend.

SPA-style shell with pipeline stepper, page routing, and AI assistant panel.

Launch:
    cd /root/IntelligenceLayer
    .venv/bin/python -m frontend.app
"""

import logging
import os
import sys
from pathlib import Path

import gradio as gr

# Ensure the project root is on sys.path so gr00t imports work
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env file from project root
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from frontend.constants import EMBODIMENT_CHOICES
from frontend.pages.assistant_panel import create_assistant_panel
from frontend.pages.dashboard import create_dashboard_sidebar
from frontend.pages.datasets import create_datasets_page
from frontend.pages.models import create_models_page
from frontend.pages.simulation import create_simulation_page
from frontend.pages.training import create_training_page
from frontend.services.assistant.agent import WybeAgent
from frontend.services.process_manager import ProcessManager
from frontend.services.server_manager import ServerManager
from frontend.services.task_runner import TaskRunner
from frontend.services.workspace import WorkspaceStore
from frontend.theme import WYBE_CSS, WybeTheme

logger = logging.getLogger(__name__)

# Page IDs for routing
PAGES = ["datasets", "training", "simulation", "models"]


def _project_choices(store: WorkspaceStore) -> list[str]:
    projects = store.list_projects()
    return [f"{p['name']} ({p['id']})" for p in projects]


def create_app() -> gr.Blocks:
    """Build the full Wybe Studio application."""

    # ── Core services ──
    store = WorkspaceStore()
    process_manager = ProcessManager()
    server_manager = ServerManager(process_manager, project_root=PROJECT_ROOT)
    task_runner = TaskRunner(store)
    task_runner.reconnect_on_startup()

    # ── AI Agent ──
    agent = WybeAgent(
        store=store,
        task_runner=task_runner,
        server_manager=server_manager,
        project_root=PROJECT_ROOT,
    )

    with gr.Blocks(title="Wybe Studio") as app:

        # ── Shared state ──
        current_page = gr.State("datasets")
        project_state = gr.State(value={})
        session_state = gr.State(value={})
        sidebar_visible = gr.State(value=False)

        # ── Shell bar ──
        with gr.Row(elem_classes="shell-bar"):
            gr.HTML('<span class="shell-logo">wybe<span class="logo-dot">.</span></span>')

            project_dropdown = gr.Dropdown(
                label="Project",
                choices=_project_choices(store),
                value=None,
                scale=1,
                allow_custom_value=False,
                container=False,
            )

            dashboard_toggle = gr.Button(
                "Dashboard",
                size="sm",
                elem_classes="sidebar-toggle-btn",
            )

        # ── Main content area ──
        with gr.Row():
            # Main panel (75%)
            with gr.Column(scale=3):
                with gr.Tabs(elem_classes="nav-tabs") as nav_tabs:
                    with gr.TabItem("Datasets", id="datasets"):
                        # New Project form — inside Datasets tab
                        with gr.Accordion("+ New Project", open=False, elem_classes="new-project-bar"):
                            with gr.Row():
                                new_proj_name = gr.Textbox(label="Name", placeholder="MyRobot")
                                new_proj_embodiment = gr.Dropdown(
                                    label="Embodiment",
                                    choices=EMBODIMENT_CHOICES,
                                    value="new_embodiment",
                                )
                                new_proj_model = gr.Textbox(
                                    label="Base Model",
                                    value="nvidia/GR00T-N1.6-3B",
                                )
                            create_proj_btn = gr.Button("Create Project", variant="primary", size="sm")
                            create_proj_status = gr.Textbox(label="", interactive=False, visible=False)

                        datasets = create_datasets_page(store, task_runner, project_state, PROJECT_ROOT)

                    with gr.TabItem("Training", id="training"):
                        training = create_training_page(store, task_runner, project_state, PROJECT_ROOT)

                    with gr.TabItem("Simulation", id="simulation"):
                        simulation = create_simulation_page(store, task_runner, project_state, PROJECT_ROOT)

                    with gr.TabItem("Models", id="models"):
                        models = create_models_page(server_manager, store, task_runner, project_state, PROJECT_ROOT)

            # Assistant panel (25%)
            with gr.Column(scale=1, elem_classes="assistant-panel"):
                assistant = create_assistant_panel(agent)

        # Dashboard sidebar overlay
        dashboard = create_dashboard_sidebar(store, server_manager, project_state)

        # ── Tab navigation → update current_page state ──

        def on_tab_select(evt: gr.SelectData):
            return PAGES[evt.index]

        nav_tabs.select(on_tab_select, outputs=[current_page])

        # ── Dashboard sidebar toggle ──

        def toggle_sidebar(is_visible):
            new_state = not is_visible
            return gr.update(visible=new_state), new_state

        dashboard_toggle.click(
            toggle_sidebar,
            inputs=[sidebar_visible],
            outputs=[dashboard["sidebar"], sidebar_visible],
        )

        # ── Project selector callbacks ──

        def select_project(choice):
            if not choice:
                return {}
            proj_id = choice.rsplit("(", 1)[-1].rstrip(")")
            proj = store.get_project(proj_id)
            return proj if proj else {}

        def create_project(name, embodiment, base_model):
            if not name.strip():
                return gr.update(), gr.update(value="Name is required", visible=True), {}
            pid = store.create_project(name, embodiment, base_model)
            choices = _project_choices(store)
            new_choice = next((c for c in choices if pid in c), None)
            proj = store.get_project(pid)
            return (
                gr.update(choices=choices, value=new_choice),
                gr.update(value=f"Project created: {pid}", visible=True),
                proj if proj else {},
            )

        project_dropdown.change(
            select_project, inputs=[project_dropdown], outputs=[project_state]
        )
        create_proj_btn.click(
            create_project,
            inputs=[new_proj_name, new_proj_embodiment, new_proj_model],
            outputs=[project_dropdown, create_proj_status, project_state],
        )

        # ── Assistant chat callbacks ──

        assistant["msg_input"].submit(
            fn=assistant["respond"],
            inputs=[
                assistant["msg_input"],
                assistant["chatbot"],
                session_state,
                project_state,
                current_page,
            ],
            outputs=[assistant["chatbot"], session_state, assistant["msg_input"]],
        )
        assistant["send_btn"].click(
            fn=assistant["respond"],
            inputs=[
                assistant["msg_input"],
                assistant["chatbot"],
                session_state,
                project_state,
                current_page,
            ],
            outputs=[assistant["chatbot"], session_state, assistant["msg_input"]],
        )

        # ── Consolidated timers ──

        # Fast timer (3s) — active runs, training logs, server health
        fast_timer = gr.Timer(3)
        fast_timer.tick(
            training["refresh_log"],
            inputs=[training["current_run_id"]],
            outputs=[training["tr_log"]],
        )
        fast_timer.tick(
            training["refresh_loss_plot"],
            inputs=[training["current_run_id"]],
            outputs=[training["tr_loss_plot"]],
        )
        fast_timer.tick(
            training["refresh_progress"],
            inputs=[training["current_run_id"]],
            outputs=[training["progress_html"]],
        )
        fast_timer.tick(
            training["refresh_checkpoints"],
            inputs=[training["current_run_id"]],
            outputs=[training["tr_checkpoints"]],
        )
        # RL training timers
        fast_timer.tick(
            training["refresh_rl_log"],
            inputs=[training["rl_run_id"]],
            outputs=[training["rl_log"]],
        )
        fast_timer.tick(
            training["refresh_rl_reward_plot"],
            inputs=[training["rl_run_id"]],
            outputs=[training["rl_reward_plot"]],
        )
        fast_timer.tick(
            training["refresh_rl_status"],
            inputs=[training["rl_run_id"]],
            outputs=[training["rl_run_status"]],
        )
        # Open-loop eval timers
        fast_timer.tick(
            simulation["refresh_ol_log"],
            inputs=[simulation["ol_run_id"]],
            outputs=[simulation["ol_log"]],
        )
        fast_timer.tick(
            simulation["refresh_ol_status"],
            inputs=[simulation["ol_run_id"]],
            outputs=[simulation["ol_status"]],
        )
        fast_timer.tick(
            simulation["refresh_ol_gallery"],
            inputs=[simulation["ol_run_id"]],
            outputs=[simulation["ol_gallery"]],
        )
        fast_timer.tick(
            simulation["refresh_ol_metrics"],
            inputs=[simulation["ol_run_id"]],
            outputs=[simulation["ol_metrics"]],
        )
        # Simulation timers
        fast_timer.tick(
            simulation["refresh_sim_log"],
            inputs=[simulation["sim_run_id"]],
            outputs=[simulation["sim_log"]],
        )
        fast_timer.tick(
            simulation["refresh_sim_status"],
            inputs=[simulation["sim_run_id"]],
            outputs=[simulation["sim_status"]],
        )
        fast_timer.tick(
            simulation["refresh_sim_metrics"],
            inputs=[simulation["sim_run_id"]],
            outputs=[simulation["sim_metrics"]],
        )
        # Dataset timers
        fast_timer.tick(
            datasets["poll_stats"],
            inputs=[datasets["stats_run_id"]],
            outputs=[datasets["stats_status"], datasets["stats_log"]],
        )
        fast_timer.tick(
            datasets["poll_convert"],
            inputs=[datasets["convert_run_id"], datasets["project_state"]],
            outputs=[datasets["convert_status"], datasets["convert_log"]],
        )
        # Models timers
        fast_timer.tick(
            models["poll_onnx"],
            inputs=[models["onnx_run_id"]],
            outputs=[models["onnx_status"], models["onnx_log"], models["trt_onnx_path"]],
        )
        fast_timer.tick(
            models["poll_trt"],
            inputs=[models["trt_run_id"]],
            outputs=[models["trt_status"], models["trt_log"], models["bench_trt_path"]],
        )
        fast_timer.tick(
            models["poll_benchmark"],
            inputs=[models["bench_run_id"], models["project_state"]],
            outputs=[models["bench_status"], models["bench_results"], models["bench_chart"]],
        )

        # Slow timer (10s) — GPU, dashboard, activity feed
        slow_timer = gr.Timer(10)
        slow_timer.tick(
            dashboard["refresh_gpu"],
            outputs=[dashboard["gpu_html"]],
        )
        slow_timer.tick(
            dashboard["refresh_server"],
            outputs=[dashboard["server_html"]],
        )
        slow_timer.tick(
            dashboard["refresh_metrics"],
            inputs=[project_state],
            outputs=[dashboard["summary_metrics"]],
        )
        slow_timer.tick(
            dashboard["refresh_activity"],
            inputs=[project_state],
            outputs=[dashboard["activity_html"]],
        )

    return app


def main():
    app = create_app()
    app.queue()
    theme = WybeTheme()
    launch_kwargs = {
        "server_name": "0.0.0.0",
        "server_port": int(os.environ.get("GRADIO_PORT", 7860)),
        "share": True,
        "show_error": True,
        "theme": theme,
        "css": WYBE_CSS,
    }
    app.launch(**launch_kwargs)


if __name__ == "__main__":
    main()
