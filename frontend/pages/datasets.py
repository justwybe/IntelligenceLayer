"""Datasets page — Teleop Demos, Urban Memory, Synth (Mimic) tabs."""

from __future__ import annotations

import json
import shutil
import traceback
from pathlib import Path

import gradio as gr

from frontend.components.dataset_card import render_dataset_cards
from frontend.constants import EMBODIMENT_CHOICES, MIMIC_ENVS
from frontend.services.task_runner import TaskRunner
from frontend.services.workspace import WorkspaceStore

# Track temp directory for episode viewer plots
_episode_tmpdir: str | None = None


def _count_episodes(dataset_path: str) -> int | None:
    episodes_file = Path(dataset_path) / "meta" / "episodes.jsonl"
    if episodes_file.exists():
        return sum(1 for _ in episodes_file.open())
    return None


def _dataset_cards_html(store: WorkspaceStore, project_id: str | None) -> str:
    datasets = store.list_datasets(project_id=project_id)
    return render_dataset_cards(datasets)


def _dataset_dropdown_choices(store: WorkspaceStore, project_id: str | None) -> list[str]:
    datasets = store.list_datasets(project_id=project_id)
    return [f"{ds['name']} | {ds['path']}" for ds in datasets]


def _load_episode_plots(dataset_path: str, episode_index: int) -> dict:
    """Load episode data and create Plotly figures."""
    global _episode_tmpdir

    result = {"video_path": None, "state_fig": None, "action_fig": None, "task_desc": "", "error": None}

    if _episode_tmpdir is not None:
        shutil.rmtree(_episode_tmpdir, ignore_errors=True)
        _episode_tmpdir = None

    p = Path(dataset_path)
    if not p.exists():
        result["error"] = f"Dataset path not found: {dataset_path}"
        return result

    ep_str = f"episode_{episode_index:06d}"
    parquet_path = p / "data" / "chunk-000" / f"{ep_str}.parquet"
    if not parquet_path.exists():
        for chunk_dir in sorted((p / "data").glob("chunk-*")):
            candidate = chunk_dir / f"{ep_str}.parquet"
            if candidate.exists():
                parquet_path = candidate
                break
        else:
            result["error"] = f"Parquet file not found for episode {episode_index}"
            return result

    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
    except Exception as exc:
        result["error"] = f"Failed to read parquet: {exc}"
        return result

    # Find video
    videos_dir = p / "videos"
    if videos_dir.exists():
        for cam_dir in sorted(videos_dir.rglob(f"{ep_str}.mp4")):
            result["video_path"] = str(cam_dir)
            break

    # Plot state trajectories with Plotly
    state_cols = [c for c in df.columns if c.startswith("observation.state")]
    if state_cols:
        try:
            import plotly.graph_objects as go
            import numpy as np
            fig = go.Figure()
            for col in state_cols:
                vals = df[col].tolist()
                if vals and isinstance(vals[0], (list, tuple)):
                    arr = np.array(vals)
                    for dim in range(arr.shape[1]):
                        fig.add_trace(go.Scatter(
                            y=arr[:, dim], mode="lines",
                            name=f"{col}[{dim}]",
                        ))
                else:
                    fig.add_trace(go.Scatter(y=vals, mode="lines", name=col))
            fig.update_layout(
                title="State Trajectories",
                xaxis_title="Timestep", yaxis_title="Value",
                template="plotly_dark",
                height=350,
                margin=dict(l=40, r=20, t=40, b=40),
            )
            result["state_fig"] = fig
        except Exception:
            pass

    # Plot action trajectories with Plotly
    action_cols = [c for c in df.columns if c.startswith("action")]
    if action_cols:
        try:
            import plotly.graph_objects as go
            import numpy as np
            fig = go.Figure()
            for col in action_cols:
                vals = df[col].tolist()
                if vals and isinstance(vals[0], (list, tuple)):
                    arr = np.array(vals)
                    for dim in range(arr.shape[1]):
                        fig.add_trace(go.Scatter(
                            y=arr[:, dim], mode="lines",
                            name=f"{col}[{dim}]",
                        ))
                else:
                    fig.add_trace(go.Scatter(y=vals, mode="lines", name=col))
            fig.update_layout(
                title="Action Trajectories",
                xaxis_title="Timestep", yaxis_title="Value",
                template="plotly_dark",
                height=350,
                margin=dict(l=40, r=20, t=40, b=40),
            )
            result["action_fig"] = fig
        except Exception:
            pass

    # Task description
    tasks_file = p / "meta" / "tasks.jsonl"
    if tasks_file.exists():
        try:
            task_index = None
            if "task_index" in df.columns and len(df) > 0:
                task_index = int(df["task_index"].iloc[0])
            tasks = [json.loads(line) for line in tasks_file.open()]
            if task_index is not None and task_index < len(tasks):
                result["task_desc"] = tasks[task_index].get("task", str(tasks[task_index]))
            elif tasks:
                result["task_desc"] = tasks[0].get("task", str(tasks[0]))
        except Exception:
            pass

    return result


def create_datasets_page(
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
) -> dict:
    """Create the datasets page. Returns dict of components."""

    with gr.Column(visible=True) as page:
        gr.HTML('<div class="page-title">Datasets</div>')
        gr.HTML('<div style="color:var(--wybe-text-muted);font-size:13px;margin-top:-16px;margin-bottom:16px">Collect & curate data</div>')

        with gr.Tabs():
            # ── Tab 1: Teleop Demos ──
            with gr.Tab("Teleop Demos"):
                # Import Dataset
                gr.HTML('<div class="section-title">Import Dataset</div>')
                with gr.Row():
                    import_name = gr.Textbox(label="Name", placeholder="cube_to_bowl_training")
                    import_path = gr.Textbox(label="Dataset Path", placeholder="/path/to/lerobot_v2_dataset")
                with gr.Row():
                    import_source = gr.Dropdown(
                        label="Source",
                        choices=["imported", "recorded", "mimic", "dreams"],
                        value="imported",
                    )
                    import_btn = gr.Button("Import Dataset", variant="primary", size="sm")
                import_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("---")

                # Episode Viewer
                gr.HTML('<div class="section-title">Episode Viewer</div>')
                with gr.Row():
                    ep_dataset_path = gr.Textbox(label="Dataset Path", placeholder="/path/to/lerobot_v2_dataset")
                    ep_index = gr.Slider(label="Episode Index", minimum=0, maximum=999, value=0, step=1)
                ep_load_btn = gr.Button("Load Episode", variant="primary", size="sm")
                ep_video = gr.Video(label="Episode Video")
                with gr.Row():
                    ep_state_plot = gr.Plot(label="State Trajectories")
                    ep_action_plot = gr.Plot(label="Action Trajectories")
                ep_task_desc = gr.Markdown(label="Task Description", value="")

                gr.Markdown("---")

                # Compute Statistics
                gr.HTML('<div class="section-title">Compute Statistics</div>')
                with gr.Row():
                    stats_dataset = gr.Dropdown(
                        label="Dataset",
                        choices=_dataset_dropdown_choices(store, None),
                        allow_custom_value=True,
                    )
                    stats_embodiment = gr.Dropdown(
                        label="Embodiment Tag",
                        choices=EMBODIMENT_CHOICES,
                        value="new_embodiment",
                    )
                stats_compute_btn = gr.Button("Compute Stats", variant="primary", size="sm")
                stats_status = gr.Textbox(label="Status", interactive=False)
                stats_log = gr.Code(label="Log Output", language=None, lines=10, interactive=False)
                stats_run_id = gr.State(value="")

            # ── Tab 2: Urban Memory ──
            with gr.Tab("Urban Memory"):
                gr.Markdown("Import data collected from deployed robot logs.")
                gr.HTML('<div class="section-title">Import from Robot Logs</div>')
                with gr.Row():
                    um_import_name = gr.Textbox(label="Name", placeholder="urban_memory_run1")
                    um_import_path = gr.Textbox(label="Dataset Path", placeholder="/path/to/robot_logs_dataset")
                um_import_btn = gr.Button("Import Dataset", variant="primary", size="sm")
                um_import_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("---")

                # Episode Viewer for urban memory
                gr.HTML('<div class="section-title">Episode Viewer</div>')
                with gr.Row():
                    um_ep_dataset_path = gr.Textbox(label="Dataset Path", placeholder="/path/to/dataset")
                    um_ep_index = gr.Slider(label="Episode Index", minimum=0, maximum=999, value=0, step=1)
                um_ep_load_btn = gr.Button("Load Episode", variant="primary", size="sm")
                um_ep_video = gr.Video(label="Episode Video")
                with gr.Row():
                    um_ep_state_plot = gr.Plot(label="State Trajectories")
                    um_ep_action_plot = gr.Plot(label="Action Trajectories")
                um_ep_task_desc = gr.Markdown(label="Task Description", value="")

            # ── Tab 3: Synth (Mimic) ──
            with gr.Tab("Synth (Mimic)"):
                gr.Markdown("Generate synthetic demonstrations using GR00T-Mimic.")

                gr.HTML('<div class="section-title">GR00T-Mimic Configuration</div>')
                with gr.Row():
                    mimic_env = gr.Dropdown(
                        label="Environment",
                        choices=MIMIC_ENVS,
                        value=MIMIC_ENVS[0] if MIMIC_ENVS else None,
                    )
                    mimic_num_demos = gr.Slider(label="Num Demos", minimum=1, maximum=1000, value=50, step=1)
                mimic_output_dir = gr.Textbox(label="Output Directory", placeholder="/path/to/mimic_output")
                mimic_generate_btn = gr.Button("Generate Demos", variant="primary", size="sm")
                mimic_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("---")

                # Convert v3 Dataset
                with gr.Accordion("Convert LeRobot v3 Dataset", open=False):
                    gr.Markdown("Download and convert a LeRobot v3 dataset from HuggingFace to v2 format.")
                    with gr.Row():
                        convert_repo_id = gr.Textbox(label="HuggingFace Repo ID", placeholder="lerobot/aloha_sim_insertion_human")
                        convert_output_dir = gr.Textbox(label="Output Directory", placeholder="/path/to/output")
                    convert_btn = gr.Button("Convert", variant="primary", size="sm")
                    convert_status = gr.Textbox(label="Status", interactive=False)
                    convert_log = gr.Code(label="Log Output", language=None, lines=10, interactive=False)
                    convert_run_id = gr.State(value="")

                gr.Markdown("---")

                # Dataset Inspector
                gr.HTML('<div class="section-title">Dataset Inspector</div>')
                detail_path = gr.Textbox(label="Dataset Path", placeholder="/path/to/dataset")
                inspect_btn = gr.Button("Inspect", size="sm")
                with gr.Row():
                    detail_info = gr.Code(label="info.json", language="json", lines=10, interactive=False)
                    detail_modality = gr.Code(label="modality.json", language="json", lines=10, interactive=False)
                detail_tasks = gr.Code(label="tasks.jsonl", language="json", lines=5, interactive=False)
                detail_stats = gr.Code(label="stats.json (summary)", language="json", lines=8, interactive=False)

        gr.Markdown("---")

        # ── Dataset Registry (shared, bottom) ──
        gr.HTML('<div class="section-title">Dataset Registry</div>')
        dataset_html = gr.HTML(value=_dataset_cards_html(store, None))
        refresh_btn = gr.Button("Refresh", size="sm")

        # ── Embodiment Config Browser ──
        with gr.Accordion("Embodiment Config Browser", open=False):
            config_selector = gr.Dropdown(
                label="Embodiment Tag",
                choices=EMBODIMENT_CHOICES,
                value="libero_panda",
            )
            config_display = gr.Code(label="Modality Config", language="json", lines=20, interactive=False)

    # ── Callbacks ──

    def refresh_datasets(proj):
        pid = proj.get("id") if proj else None
        return (
            _dataset_cards_html(store, pid),
            gr.update(choices=_dataset_dropdown_choices(store, pid)),
        )

    def import_dataset(name, path, source, proj):
        if not name.strip() or not path.strip():
            return "Name and path are required"
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first"
        p = Path(path)
        if not p.exists():
            return f"Path does not exist: {path}"
        episode_count = _count_episodes(path)
        did = store.register_dataset(
            project_id=pid, name=name, path=str(p.resolve()),
            source=source, episode_count=episode_count,
        )
        count_msg = f" ({episode_count} episodes)" if episode_count else ""
        return f"Dataset registered: {did}{count_msg}"

    def import_urban_memory(name, path, proj):
        if not name.strip() or not path.strip():
            return "Name and path are required"
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first"
        p = Path(path)
        if not p.exists():
            return f"Path does not exist: {path}"
        episode_count = _count_episodes(path)
        did = store.register_dataset(
            project_id=pid, name=name, path=str(p.resolve()),
            source="urban_memory", episode_count=episode_count,
        )
        count_msg = f" ({episode_count} episodes)" if episode_count else ""
        return f"Dataset registered: {did}{count_msg}"

    def generate_mimic(env, num_demos, output_dir, proj):
        if not output_dir.strip():
            return "Output directory is required"
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first"
        return f"GR00T-Mimic generation queued: env={env}, demos={int(num_demos)}, output={output_dir}"

    def inspect_dataset(path):
        if not path.strip():
            return "", "", "", ""
        p = Path(path)
        if not p.exists():
            return f"Path not found: {path}", "", "", ""

        info_str = modality_str = tasks_str = stats_str = ""

        info_file = p / "meta" / "info.json"
        if info_file.exists():
            info_str = info_file.read_text()
        modality_file = p / "meta" / "modality.json"
        if modality_file.exists():
            modality_str = modality_file.read_text()
        tasks_file = p / "meta" / "tasks.jsonl"
        if tasks_file.exists():
            tasks_str = tasks_file.read_text()
        stats_file = p / "meta" / "stats.json"
        if stats_file.exists():
            try:
                stats_data = json.loads(stats_file.read_text())
                summary = {}
                for key in list(stats_data.keys())[:20]:
                    val = stats_data[key]
                    if isinstance(val, dict):
                        summary[key] = {k: type(v).__name__ for k, v in val.items()}
                    else:
                        summary[key] = str(val)[:100]
                stats_str = json.dumps(summary, indent=2)
            except Exception:
                stats_str = stats_file.read_text()[:2000]

        return info_str, modality_str, tasks_str, stats_str

    def show_config(tag):
        try:
            import sys
            sys.path.insert(0, project_root)
            from gr00t.configs.data.embodiment_configs import MODALITY_CONFIGS
            from gr00t.data.utils import to_json_serializable
            cfg = MODALITY_CONFIGS.get(tag)
            if cfg is None:
                return f"No config found for '{tag}'"
            serializable = {}
            for modality, mc in cfg.items():
                serializable[modality] = to_json_serializable(mc)
            return json.dumps(serializable, indent=2)
        except Exception as exc:
            return f"Error loading config: {exc}\n{traceback.format_exc()}"

    def launch_stats(dataset_choice, embodiment, proj):
        dataset_path = dataset_choice.split("|")[-1].strip() if "|" in dataset_choice else dataset_choice
        if not dataset_path.strip():
            return "Dataset path is required", ""
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first", ""
        config = {"dataset_path": dataset_path, "embodiment_tag": embodiment}
        run_id = store.create_run(project_id=pid, run_type="stats_computation", config=config)
        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        cmd = [venv_python, "-m", "gr00t.data.stats", "--dataset-path", dataset_path, "--embodiment-tag", embodiment]
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id

    def poll_stats(run_id):
        if not run_id:
            return "", ""
        status = task_runner.status(run_id)
        log = task_runner.tail_log(run_id, 30)
        status_msg = f"Status: {status}"
        if status in ("completed", "failed", "stopped"):
            status_msg += f" — stats computation {status}"
        return status_msg, log

    def launch_conversion(repo_id, output_dir, proj):
        if not repo_id.strip() or not output_dir.strip():
            return "Repo ID and output dir are required", ""
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first", ""
        config = {"repo_id": repo_id, "output_dir": output_dir}
        run_id = store.create_run(project_id=pid, run_type="conversion", config=config)
        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        cmd = [venv_python, "scripts/lerobot_conversion/convert_v3_to_v2.py", "--repo-id", repo_id, "--root", output_dir]
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id

    def poll_convert(run_id, proj):
        if not run_id:
            return "", ""
        status = task_runner.status(run_id)
        log = task_runner.tail_log(run_id, 30)
        status_msg = f"Status: {status}"
        if status == "completed":
            run = store.get_run(run_id)
            if run:
                try:
                    config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
                    output_dir = config.get("output_dir", "")
                    repo_id = config.get("repo_id", "")
                    pid = proj.get("id") if proj else None
                    if pid and output_dir:
                        existing = store.list_datasets(project_id=pid)
                        if not any(d["path"] == output_dir for d in existing):
                            ep_count = _count_episodes(output_dir)
                            ds_name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
                            store.register_dataset(project_id=pid, name=ds_name, path=output_dir, source="imported", episode_count=ep_count)
                            status_msg += " — dataset auto-registered"
                except Exception:
                    pass
        return status_msg, log

    def load_episode(dataset_path, episode_index):
        if not dataset_path.strip():
            return None, None, None, "Provide a dataset path"
        data = _load_episode_plots(dataset_path, int(episode_index))
        if data["error"]:
            return None, None, None, f"**Error:** {data['error']}"
        task = data["task_desc"]
        task_md = f"**Task:** {task}" if task else ""
        return data["video_path"], data["state_fig"], data["action_fig"], task_md

    # Wire callbacks
    refresh_btn.click(refresh_datasets, inputs=[project_state], outputs=[dataset_html, stats_dataset])
    import_btn.click(import_dataset, inputs=[import_name, import_path, import_source, project_state], outputs=[import_status])
    um_import_btn.click(import_urban_memory, inputs=[um_import_name, um_import_path, project_state], outputs=[um_import_status])
    mimic_generate_btn.click(generate_mimic, inputs=[mimic_env, mimic_num_demos, mimic_output_dir, project_state], outputs=[mimic_status])
    inspect_btn.click(inspect_dataset, inputs=[detail_path], outputs=[detail_info, detail_modality, detail_tasks, detail_stats])
    config_selector.change(show_config, inputs=[config_selector], outputs=[config_display])
    stats_compute_btn.click(launch_stats, inputs=[stats_dataset, stats_embodiment, project_state], outputs=[stats_status, stats_run_id])
    convert_btn.click(launch_conversion, inputs=[convert_repo_id, convert_output_dir, project_state], outputs=[convert_status, convert_run_id])
    ep_load_btn.click(load_episode, inputs=[ep_dataset_path, ep_index], outputs=[ep_video, ep_state_plot, ep_action_plot, ep_task_desc])
    um_ep_load_btn.click(load_episode, inputs=[um_ep_dataset_path, um_ep_index], outputs=[um_ep_video, um_ep_state_plot, um_ep_action_plot, um_ep_task_desc])

    return {
        "page": page,
        "poll_stats": poll_stats,
        "poll_convert": poll_convert,
        "stats_run_id": stats_run_id,
        "stats_status": stats_status,
        "stats_log": stats_log,
        "convert_run_id": convert_run_id,
        "convert_status": convert_status,
        "convert_log": convert_log,
        "project_state": project_state,
    }
