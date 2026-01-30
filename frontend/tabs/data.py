from __future__ import annotations

"""Data tab — dataset registry, import, stats computation, v3→v2 conversion, episode viewer."""

import json
import os
import shutil
import tempfile
import traceback
from pathlib import Path

import gradio as gr

from frontend.services.task_runner import TaskRunner
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

# Track temp directory for episode viewer plots so we can clean up between calls
_episode_tmpdir: str | None = None


def _count_episodes(dataset_path: str) -> int | None:
    """Try to count episodes from the LeRobot v2 metadata."""
    episodes_file = Path(dataset_path) / "meta" / "episodes.jsonl"
    if episodes_file.exists():
        return sum(1 for _ in episodes_file.open())
    return None


def _dataset_table(store: WorkspaceStore, project_id: str | None) -> list[list]:
    datasets = store.list_datasets(project_id=project_id)
    if not datasets:
        return [["No datasets registered", "", "", "", ""]]
    rows = []
    for ds in datasets:
        ts = ds["created_at"]
        if ts and len(ts) > 16:
            ts = ts[:16]
        rows.append([
            ds["name"],
            ds["path"],
            str(ds.get("episode_count") or "-"),
            ds.get("source", "imported"),
            ts or "",
        ])
    return rows


def _load_episode_data(dataset_path: str, episode_index: int) -> dict:
    """Load episode data from a LeRobot v2 dataset directory.

    Reads parquet for state/action data, finds video file, reads task description.
    Returns a dict with keys: video_path, state_plot_path, action_plot_path, task_desc, error.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    global _episode_tmpdir

    result = {"video_path": None, "state_plot_path": None, "action_plot_path": None, "task_desc": "", "error": None}

    # Clean up previous temp dir before creating a new one
    if _episode_tmpdir is not None:
        shutil.rmtree(_episode_tmpdir, ignore_errors=True)
        _episode_tmpdir = None

    p = Path(dataset_path)

    if not p.exists():
        result["error"] = f"Dataset path not found: {dataset_path}"
        return result

    # Format episode number with zero-padding
    ep_str = f"episode_{episode_index:06d}"

    # Find parquet file
    parquet_path = p / "data" / "chunk-000" / f"{ep_str}.parquet"
    if not parquet_path.exists():
        # Try alternate chunk directories
        for chunk_dir in sorted((p / "data").glob("chunk-*")):
            candidate = chunk_dir / f"{ep_str}.parquet"
            if candidate.exists():
                parquet_path = candidate
                break
        else:
            result["error"] = f"Parquet file not found for episode {episode_index}"
            return result

    # Read parquet data
    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
    except Exception as exc:
        result["error"] = f"Failed to read parquet: {exc}"
        return result

    # Find video file
    videos_dir = p / "videos"
    if videos_dir.exists():
        for cam_dir in sorted(videos_dir.rglob(f"{ep_str}.mp4")):
            result["video_path"] = str(cam_dir)
            break

    # Plot state trajectories
    state_cols = [c for c in df.columns if c.startswith("observation.state")]
    if state_cols:
        try:
            _episode_tmpdir = tempfile.mkdtemp(prefix="wybe_episode_")
            fig, ax = plt.subplots(figsize=(8, 4))
            for col in state_cols:
                vals = df[col].tolist()
                # Handle list/array columns
                if vals and isinstance(vals[0], (list, tuple)):
                    import numpy as np
                    arr = np.array(vals)
                    for dim in range(arr.shape[1]):
                        label = f"{col}[{dim}]"
                        ax.plot(arr[:, dim], label=label, linewidth=0.8)
                else:
                    ax.plot(vals, label=col, linewidth=0.8)
            ax.set_xlabel("Timestep")
            ax.set_ylabel("Value")
            ax.set_title("State Trajectories")
            ax.legend(fontsize=6, ncol=2, loc="upper right")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            state_path = os.path.join(_episode_tmpdir, "state_plot.png")
            fig.savefig(state_path, dpi=100)
            plt.close(fig)
            result["state_plot_path"] = state_path
        except Exception as exc:
            result.setdefault("warnings", []).append(f"State plot failed: {exc}")

    # Plot action trajectories
    action_cols = [c for c in df.columns if c.startswith("action")]
    if action_cols:
        try:
            if _episode_tmpdir is None:
                _episode_tmpdir = tempfile.mkdtemp(prefix="wybe_episode_")
            fig, ax = plt.subplots(figsize=(8, 4))
            for col in action_cols:
                vals = df[col].tolist()
                if vals and isinstance(vals[0], (list, tuple)):
                    import numpy as np
                    arr = np.array(vals)
                    for dim in range(arr.shape[1]):
                        label = f"{col}[{dim}]"
                        ax.plot(arr[:, dim], label=label, linewidth=0.8)
                else:
                    ax.plot(vals, label=col, linewidth=0.8)
            ax.set_xlabel("Timestep")
            ax.set_ylabel("Value")
            ax.set_title("Action Trajectories")
            ax.legend(fontsize=6, ncol=2, loc="upper right")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            action_path = os.path.join(_episode_tmpdir, "action_plot.png")
            fig.savefig(action_path, dpi=100)
            plt.close(fig)
            result["action_plot_path"] = action_path
        except Exception as exc:
            result.setdefault("warnings", []).append(f"Action plot failed: {exc}")

    # Read task description
    tasks_file = p / "meta" / "tasks.jsonl"
    if tasks_file.exists():
        try:
            # Get task_index from the episode data if available
            task_index = None
            if "task_index" in df.columns and len(df) > 0:
                task_index = int(df["task_index"].iloc[0])

            tasks = []
            for line in tasks_file.open():
                tasks.append(json.loads(line))

            if task_index is not None and task_index < len(tasks):
                result["task_desc"] = tasks[task_index].get("task", str(tasks[task_index]))
            elif tasks:
                result["task_desc"] = tasks[0].get("task", str(tasks[0]))
        except Exception:
            pass

    return result


def create_data_tab(
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
):
    with gr.Tab("Data"):
        gr.Markdown("## Data")

        # ── Dataset Registry ──
        gr.Markdown("### Dataset Registry")
        dataset_table = gr.Dataframe(
            headers=["Name", "Path", "Episodes", "Source", "Created"],
            label="Registered Datasets",
            interactive=False,
            value=_dataset_table(store, None),
        )
        refresh_btn = gr.Button("Refresh", size="sm")

        gr.Markdown("---")

        # ── Import Dataset ──
        gr.Markdown("### Import Dataset")
        gr.Markdown(
            "Point to a LeRobot v2 directory on disk to register it with this project."
        )
        with gr.Row():
            import_name = gr.Textbox(
                label="Name",
                placeholder="cube_to_bowl_training",
            )
            import_path = gr.Textbox(
                label="Dataset Path",
                placeholder="/path/to/lerobot_v2_dataset",
            )
        with gr.Row():
            import_source = gr.Dropdown(
                label="Source",
                choices=["imported", "recorded", "mimic", "dreams"],
                value="imported",
            )
            import_btn = gr.Button("Import Dataset", variant="primary", size="sm")
        import_status = gr.Textbox(label="Status", interactive=False)

        gr.Markdown("---")

        # ── A1: Compute Statistics ──
        gr.Markdown("### Compute Statistics")
        with gr.Row():
            stats_dataset_path = gr.Textbox(
                label="Dataset Path",
                placeholder="/path/to/lerobot_v2_dataset",
            )
            stats_embodiment = gr.Dropdown(
                label="Embodiment Tag",
                choices=EMBODIMENT_CHOICES,
                value="new_embodiment",
            )
        stats_compute_btn = gr.Button("Compute Stats", variant="primary", size="sm")
        stats_status = gr.Textbox(label="Status", interactive=False)
        stats_log = gr.Textbox(label="Log Output", lines=10, interactive=False)
        stats_run_id = gr.State(value="")

        gr.Markdown("---")

        # ── A2: Convert LeRobot v3 Dataset ──
        gr.Markdown("### Convert LeRobot v3 Dataset")
        gr.Markdown("Download and convert a LeRobot v3 dataset from HuggingFace to v2 format.")
        with gr.Row():
            convert_repo_id = gr.Textbox(
                label="HuggingFace Repo ID",
                placeholder="lerobot/aloha_sim_insertion_human",
            )
            convert_output_dir = gr.Textbox(
                label="Output Directory",
                placeholder="/path/to/output",
            )
        convert_btn = gr.Button("Convert", variant="primary", size="sm")
        convert_status = gr.Textbox(label="Status", interactive=False)
        convert_log = gr.Textbox(label="Log Output", lines=10, interactive=False)
        convert_run_id = gr.State(value="")

        gr.Markdown("---")

        # ── Dataset Details ──
        gr.Markdown("### Dataset Details")
        detail_path = gr.Textbox(
            label="Dataset Path (paste or select from table above)",
            placeholder="/path/to/dataset",
        )
        inspect_btn = gr.Button("Inspect", size="sm")
        with gr.Row():
            detail_info = gr.Code(
                label="info.json",
                language="json",
                lines=10,
                interactive=False,
            )
            detail_modality = gr.Code(
                label="modality.json",
                language="json",
                lines=10,
                interactive=False,
            )
        detail_tasks = gr.Code(
            label="tasks.jsonl",
            language="json",
            lines=5,
            interactive=False,
        )
        detail_stats = gr.Code(
            label="stats.json (summary)",
            language="json",
            lines=8,
            interactive=False,
        )

        gr.Markdown("---")

        # ── A3: Episode Viewer ──
        gr.Markdown("### Episode Viewer")
        with gr.Row():
            ep_dataset_path = gr.Textbox(
                label="Dataset Path",
                placeholder="/path/to/lerobot_v2_dataset",
            )
            ep_index = gr.Number(label="Episode Index", value=0, precision=0)
        ep_load_btn = gr.Button("Load Episode", variant="primary", size="sm")
        ep_video = gr.Video(label="Episode Video")
        with gr.Row():
            ep_state_plot = gr.Image(label="State Trajectories")
            ep_action_plot = gr.Image(label="Action Trajectories")
        ep_task_desc = gr.Markdown(label="Task Description", value="")

        gr.Markdown("---")

        # ── Embodiment Config Browser ──
        gr.Markdown("### Embodiment Config Browser")
        config_selector = gr.Dropdown(
            label="Embodiment Tag",
            choices=EMBODIMENT_CHOICES,
            value="libero_panda",
        )
        config_display = gr.Code(
            label="Modality Config",
            language="json",
            lines=20,
            interactive=False,
        )

        # ── Callbacks ──

        def refresh_datasets(proj):
            pid = proj.get("id") if proj else None
            return _dataset_table(store, pid)

        def import_dataset(name, path, source, proj):
            if not name.strip() or not path.strip():
                return "Name and path are required"
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first"
            p = Path(path)
            if not p.exists():
                return f"Path does not exist: {path}"
            if not p.is_dir():
                return f"Path is not a directory: {path}"
            episode_count = _count_episodes(path)
            did = store.register_dataset(
                project_id=pid,
                name=name,
                path=str(p.resolve()),
                source=source,
                episode_count=episode_count,
            )
            count_msg = f" ({episode_count} episodes)" if episode_count else ""
            return f"Dataset registered: {did}{count_msg}"

        def inspect_dataset(path):
            if not path.strip():
                return "", "", "", ""
            p = Path(path)
            if not p.exists():
                return f"Path not found: {path}", "", "", ""

            info_str = ""
            modality_str = ""
            tasks_str = ""
            stats_str = ""

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
                    # Show just the top-level keys and shapes
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

        # ── A1: Stats computation callbacks ──

        def launch_stats(dataset_path, embodiment, proj):
            if not dataset_path.strip():
                return "Dataset path is required", ""
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first", ""

            config = {
                "dataset_path": dataset_path,
                "embodiment_tag": embodiment,
            }
            run_id = store.create_run(
                project_id=pid,
                run_type="stats_computation",
                config=config,
            )

            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            cmd = [
                venv_python,
                "-m", "gr00t.data.stats",
                "--dataset-path", dataset_path,
                "--embodiment-tag", embodiment,
            ]

            msg = task_runner.launch(run_id, cmd, cwd=project_root)
            return msg, run_id

        def poll_stats_status(run_id):
            if not run_id:
                return "", ""
            status = task_runner.status(run_id)
            log = task_runner.tail_log(run_id, 30)
            status_msg = f"Status: {status}"
            if status in ("completed", "failed", "stopped"):
                status_msg += " — stats computation finished" if status == "completed" else f" — {status}"
            return status_msg, log

        # ── A2: Conversion callbacks ──

        def launch_conversion(repo_id, output_dir, proj):
            if not repo_id.strip():
                return "HuggingFace Repo ID is required", ""
            if not output_dir.strip():
                return "Output directory is required", ""
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first", ""

            config = {
                "repo_id": repo_id,
                "output_dir": output_dir,
            }
            run_id = store.create_run(
                project_id=pid,
                run_type="conversion",
                config=config,
            )

            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            cmd = [
                venv_python,
                "scripts/lerobot_conversion/convert_v3_to_v2.py",
                "--repo-id", repo_id,
                "--root", output_dir,
            ]

            msg = task_runner.launch(run_id, cmd, cwd=project_root)
            return msg, run_id

        def poll_convert_status(run_id, proj):
            if not run_id:
                return "", ""
            status = task_runner.status(run_id)
            log = task_runner.tail_log(run_id, 30)
            status_msg = f"Status: {status}"

            # Auto-register dataset on completion
            if status == "completed":
                run = store.get_run(run_id)
                if run:
                    try:
                        config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
                        output_dir = config.get("output_dir", "")
                        repo_id = config.get("repo_id", "")
                        pid = proj.get("id") if proj else None
                        if pid and output_dir:
                            # Check if already registered
                            existing = store.list_datasets(project_id=pid)
                            already = any(d["path"] == output_dir for d in existing)
                            if not already:
                                ep_count = _count_episodes(output_dir)
                                ds_name = repo_id.split("/")[-1] if "/" in repo_id else repo_id
                                store.register_dataset(
                                    project_id=pid,
                                    name=ds_name,
                                    path=output_dir,
                                    source="imported",
                                    episode_count=ep_count,
                                )
                                status_msg += " — dataset auto-registered"
                    except Exception:
                        pass

            return status_msg, log

        # ── A3: Episode viewer callback ──

        def load_episode(dataset_path, episode_index):
            if not dataset_path.strip():
                return None, None, None, "Provide a dataset path"
            data = _load_episode_data(dataset_path, int(episode_index))
            if data["error"]:
                return None, None, None, f"**Error:** {data['error']}"

            video = data["video_path"]
            state_img = data["state_plot_path"]
            action_img = data["action_plot_path"]
            task = data["task_desc"]
            task_md = f"**Task:** {task}" if task else ""

            return video, state_img, action_img, task_md

        # ── Wire up callbacks ──

        refresh_btn.click(
            refresh_datasets, inputs=[project_state], outputs=[dataset_table]
        )
        import_btn.click(
            import_dataset,
            inputs=[import_name, import_path, import_source, project_state],
            outputs=[import_status],
        )
        inspect_btn.click(
            inspect_dataset,
            inputs=[detail_path],
            outputs=[detail_info, detail_modality, detail_tasks, detail_stats],
        )
        config_selector.change(
            show_config, inputs=[config_selector], outputs=[config_display]
        )

        # A1: Stats
        stats_compute_btn.click(
            launch_stats,
            inputs=[stats_dataset_path, stats_embodiment, project_state],
            outputs=[stats_status, stats_run_id],
        )
        stats_timer = gr.Timer(5)
        stats_timer.tick(
            poll_stats_status,
            inputs=[stats_run_id],
            outputs=[stats_status, stats_log],
        )

        # A2: Conversion
        convert_btn.click(
            launch_conversion,
            inputs=[convert_repo_id, convert_output_dir, project_state],
            outputs=[convert_status, convert_run_id],
        )
        convert_timer = gr.Timer(5)
        convert_timer.tick(
            poll_convert_status,
            inputs=[convert_run_id, project_state],
            outputs=[convert_status, convert_log],
        )

        # A3: Episode viewer
        ep_load_btn.click(
            load_episode,
            inputs=[ep_dataset_path, ep_index],
            outputs=[ep_video, ep_state_plot, ep_action_plot, ep_task_desc],
        )
