"""Main entry point for Wybe Studio — the IntelligenceLayer frontend.

Launch:
    cd /root/IntelligenceLayer
    .venv/bin/python -m frontend.app
"""

import os
import sys
from pathlib import Path

import gradio as gr

# Ensure the project root is on sys.path so gr00t imports work
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from frontend.services.process_manager import ProcessManager
from frontend.services.server_manager import ServerManager
from frontend.services.task_runner import TaskRunner
from frontend.services.workspace import WorkspaceStore
from frontend.tabs.data import create_data_tab
from frontend.tabs.deploy import create_deploy_tab
from frontend.tabs.evaluate import create_evaluate_tab
from frontend.tabs.train import create_train_tab
from frontend.tabs.workbench import create_workbench_tab

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


def create_app() -> gr.Blocks:
    # Core services
    store = WorkspaceStore()
    process_manager = ProcessManager()
    server_manager = ServerManager(process_manager, project_root=PROJECT_ROOT)
    task_runner = TaskRunner(store)

    # Clean up stale runs on startup
    task_runner.reconnect_on_startup()

    with gr.Blocks(
        title="Wybe Studio",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container { max-width: 1400px; margin: auto; }
        footer { display: none !important; }
        .project-bar { margin-bottom: 1rem; }
        """,
    ) as app:

        # ── Project selector bar ──
        with gr.Row(elem_classes="project-bar"):
            gr.Markdown("# Wybe Studio", scale=3)
            project_dropdown = gr.Dropdown(
                label="Project",
                choices=_project_choices(store),
                value=None,
                scale=2,
                allow_custom_value=False,
            )
            refresh_projects_btn = gr.Button("Refresh", size="sm", scale=0)

        # ── New project form (collapsible) ──
        with gr.Accordion("New Project", open=False):
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

        # Shared state: currently selected project dict
        project_state = gr.State(value={})

        # ── Tabs ──
        create_workbench_tab(server_manager, store, project_state)
        create_data_tab(store, task_runner, project_state, PROJECT_ROOT)
        create_train_tab(store, task_runner, project_state, PROJECT_ROOT)
        create_evaluate_tab(store, task_runner, project_state, PROJECT_ROOT)
        create_deploy_tab(server_manager, store, task_runner, project_state, PROJECT_ROOT)

        # ── Project selector callbacks ──

        def refresh_project_list():
            choices = _project_choices(store)
            return gr.update(choices=choices, value=None)

        def select_project(choice):
            if not choice:
                return {}
            # choice is "name (id)" — extract id
            proj_id = choice.rsplit("(", 1)[-1].rstrip(")")
            proj = store.get_project(proj_id)
            return proj if proj else {}

        def create_project(name, embodiment, base_model):
            if not name.strip():
                return (
                    gr.update(),
                    gr.update(value="Name is required", visible=True),
                    {},
                )
            pid = store.create_project(name, embodiment, base_model)
            choices = _project_choices(store)
            new_choice = next(
                (c for c in choices if pid in c), None
            )
            proj = store.get_project(pid)
            return (
                gr.update(choices=choices, value=new_choice),
                gr.update(value=f"Project created: {pid}", visible=True),
                proj if proj else {},
            )

        refresh_projects_btn.click(
            refresh_project_list, outputs=[project_dropdown]
        )
        project_dropdown.change(
            select_project, inputs=[project_dropdown], outputs=[project_state]
        )
        create_proj_btn.click(
            create_project,
            inputs=[new_proj_name, new_proj_embodiment, new_proj_model],
            outputs=[project_dropdown, create_proj_status, project_state],
        )

    return app


def _project_choices(store: WorkspaceStore) -> list[str]:
    projects = store.list_projects()
    return [f"{p['name']} ({p['id']})" for p in projects]


def main():
    app = create_app()
    app.queue()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("GRADIO_PORT", 7860)),
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
