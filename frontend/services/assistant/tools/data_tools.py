"""Data tools — dataset import, inspection, statistics, conversion, episode browsing."""

from __future__ import annotations

import json
from pathlib import Path

from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolResult, json_output


def _import_dataset(ctx: ToolContext, args: dict) -> ToolResult:
    name = args.get("name", "").strip()
    path = args.get("path", "").strip()
    source = args.get("source", "imported")
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)
    if not name or not path:
        return ToolResult(output="Both name and path are required.", is_error=True)

    p = Path(path)
    if not p.exists():
        return ToolResult(output=f"Path does not exist: {path}", is_error=True)

    # Count episodes
    episodes_file = p / "meta" / "episodes.jsonl"
    episode_count = None
    if episodes_file.exists():
        episode_count = sum(1 for _ in episodes_file.open())

    did = ctx.store.register_dataset(
        project_id=pid,
        name=name,
        path=str(p.resolve()),
        source=source,
        episode_count=episode_count,
    )
    count_msg = f" ({episode_count} episodes)" if episode_count else ""
    return ToolResult(output=f"Dataset registered successfully.\nID: {did}\nName: {name}{count_msg}")


def _inspect_dataset(ctx: ToolContext, args: dict) -> ToolResult:
    path = args.get("path", "").strip()
    if not path:
        return ToolResult(output="Dataset path is required.", is_error=True)
    p = Path(path)
    if not p.exists():
        return ToolResult(output=f"Path not found: {path}", is_error=True)

    result = {}

    info_file = p / "meta" / "info.json"
    if info_file.exists():
        try:
            result["info"] = json.loads(info_file.read_text())
        except Exception:
            result["info"] = "Failed to parse"

    modality_file = p / "meta" / "modality.json"
    if modality_file.exists():
        try:
            result["modality"] = json.loads(modality_file.read_text())
        except Exception:
            result["modality"] = "Failed to parse"

    tasks_file = p / "meta" / "tasks.jsonl"
    if tasks_file.exists():
        try:
            tasks = [json.loads(line) for line in tasks_file.open()]
            result["tasks"] = tasks
        except Exception:
            result["tasks"] = "Failed to parse"

    stats_file = p / "meta" / "stats.json"
    if stats_file.exists():
        try:
            stats = json.loads(stats_file.read_text())
            result["stats_keys"] = list(stats.keys())[:20]
            result["has_stats"] = True
        except Exception:
            result["has_stats"] = False
    else:
        result["has_stats"] = False

    episodes_file = p / "meta" / "episodes.jsonl"
    if episodes_file.exists():
        result["episode_count"] = sum(1 for _ in episodes_file.open())

    return ToolResult(output=json_output(result))


def _compute_statistics(ctx: ToolContext, args: dict) -> ToolResult:
    dataset_path = args.get("dataset_path", "").strip()
    embodiment_tag = args.get("embodiment_tag", "new_embodiment")
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)
    if not dataset_path:
        return ToolResult(output="dataset_path is required.", is_error=True)

    config = {"dataset_path": dataset_path, "embodiment_tag": embodiment_tag}
    run_id = ctx.store.create_run(project_id=pid, run_type="stats_computation", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "-m", "gr00t.data.stats",
        "--dataset-path", dataset_path,
        "--embodiment-tag", embodiment_tag,
    ]
    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"Statistics computation launched.\nRun ID: {run_id}\n{msg}")


def _convert_dataset_v3_to_v2(ctx: ToolContext, args: dict) -> ToolResult:
    repo_id = args.get("repo_id", "").strip()
    output_dir = args.get("output_dir", "").strip()
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)
    if not repo_id or not output_dir:
        return ToolResult(output="Both repo_id and output_dir are required.", is_error=True)

    config = {"repo_id": repo_id, "output_dir": output_dir}
    run_id = ctx.store.create_run(project_id=pid, run_type="conversion", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "scripts/lerobot_conversion/convert_v3_to_v2.py",
        "--repo-id", repo_id,
        "--root", output_dir,
    ]
    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"Conversion launched.\nRun ID: {run_id}\n{msg}")


def _browse_episode(ctx: ToolContext, args: dict) -> ToolResult:
    dataset_path = args.get("dataset_path", "").strip()
    episode_index = int(args.get("episode_index", 0))
    if not dataset_path:
        return ToolResult(output="dataset_path is required.", is_error=True)

    p = Path(dataset_path)
    if not p.exists():
        return ToolResult(output=f"Path not found: {dataset_path}", is_error=True)

    ep_str = f"episode_{episode_index:06d}"
    parquet_path = p / "data" / "chunk-000" / f"{ep_str}.parquet"

    if not parquet_path.exists():
        for chunk_dir in sorted((p / "data").glob("chunk-*")):
            candidate = chunk_dir / f"{ep_str}.parquet"
            if candidate.exists():
                parquet_path = candidate
                break
        else:
            return ToolResult(output=f"Episode {episode_index} not found.", is_error=True)

    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
        info = {
            "episode_index": episode_index,
            "num_timesteps": len(df),
            "columns": list(df.columns),
            "state_columns": [c for c in df.columns if "state" in c.lower()],
            "action_columns": [c for c in df.columns if "action" in c.lower()],
        }

        # Check for video
        videos_dir = p / "videos"
        if videos_dir.exists():
            for vid in videos_dir.rglob(f"{ep_str}.mp4"):
                info["video_path"] = str(vid)
                break

        # Read task description
        tasks_file = p / "meta" / "tasks.jsonl"
        if tasks_file.exists():
            tasks = [json.loads(line) for line in tasks_file.open()]
            if "task_index" in df.columns and len(df) > 0:
                task_idx = int(df["task_index"].iloc[0])
                if task_idx < len(tasks):
                    info["task"] = tasks[task_idx].get("task", str(tasks[task_idx]))

        return ToolResult(output=json_output(info))
    except Exception as exc:
        return ToolResult(output=f"Error reading episode: {exc}", is_error=True)


DATA_TOOLS = [
    ToolDef(
        name="import_dataset",
        description="Register a LeRobot v2 dataset directory with the current project.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name for the dataset"},
                "path": {"type": "string", "description": "Absolute path to the LeRobot v2 dataset directory"},
                "source": {"type": "string", "description": "Source label", "enum": ["imported", "recorded", "mimic", "dreams"]},
            },
            "required": ["name", "path"],
        },
        handler=_import_dataset,
        category="data",
    ),
    ToolDef(
        name="inspect_dataset",
        description="Inspect a dataset directory — reads metadata, tasks, stats summary.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Dataset directory path"},
            },
            "required": ["path"],
        },
        handler=_inspect_dataset,
        category="data",
    ),
    ToolDef(
        name="compute_statistics",
        description="Launch statistics computation for a dataset (required before training).",
        parameters={
            "type": "object",
            "properties": {
                "dataset_path": {"type": "string", "description": "Path to the dataset"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag for stats computation"},
            },
            "required": ["dataset_path"],
        },
        handler=_compute_statistics,
        category="data",
    ),
    ToolDef(
        name="convert_dataset_v3_to_v2",
        description="Download and convert a LeRobot v3 dataset from HuggingFace to v2 format.",
        parameters={
            "type": "object",
            "properties": {
                "repo_id": {"type": "string", "description": "HuggingFace repo ID (e.g., lerobot/aloha_sim_insertion_human)"},
                "output_dir": {"type": "string", "description": "Output directory for the converted dataset"},
            },
            "required": ["repo_id", "output_dir"],
        },
        handler=_convert_dataset_v3_to_v2,
        category="data",
    ),
    ToolDef(
        name="browse_episode",
        description="Browse an episode from a dataset — shows timesteps, columns, task info.",
        parameters={
            "type": "object",
            "properties": {
                "dataset_path": {"type": "string", "description": "Path to the dataset"},
                "episode_index": {"type": "integer", "description": "Episode index to browse", "default": 0},
            },
            "required": ["dataset_path"],
        },
        handler=_browse_episode,
        category="data",
    ),
]
