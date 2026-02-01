"""Project context builder — gathers state for the system prompt."""

from __future__ import annotations

import json
import os
from typing import Any

from frontend.services.gpu_monitor import get_gpu_info


def build_project_context(
    store: Any,
    server_manager: Any,
    project_id: str | None = None,
    current_page: str = "datasets",
) -> str:
    """Build a context string describing the current project state.

    This is injected into the system prompt so the assistant knows
    what's happening without needing a tool call on every turn.
    """
    page_labels = {
        "datasets": "Datasets — data import, curation, and statistics",
        "training": "Training — GR00T finetune and Isaac Lab RL",
        "simulation": "Simulation — Isaac Sim eval, open-loop eval, model comparison",
        "models": "Models — registry, optimization, deployment",
    }
    page_line = f"**Current Page**: {page_labels.get(current_page, current_page)} — the user is currently viewing this stage"

    env_lines = _build_environment_context()
    env_block = "\n".join(env_lines)

    if not project_id:
        projects = store.list_projects()
        if not projects:
            return f"{page_line}\n\n{env_block}\n\nNo projects exist yet. The user needs to create their first project."
        project_list = ", ".join(f'"{p["name"]}" ({p["id"]})' for p in projects[:5])
        return f"{page_line}\n\n{env_block}\n\nNo project selected. Available projects: {project_list}"

    project = store.get_project(project_id)
    if not project:
        return f"Project {project_id} not found."

    lines = [
        page_line,
        "",
        *env_lines,
        "",
        f"**Active Project**: {project['name']} (ID: {project['id']})",
        f"**Embodiment**: {project['embodiment_tag']}",
        f"**Base Model**: {project['base_model']}",
    ]

    # Datasets
    datasets = store.list_datasets(project_id=project_id)
    if datasets:
        ds_lines = []
        for d in datasets[:5]:
            ep = f" ({d['episode_count']} episodes)" if d.get("episode_count") else ""
            ds_lines.append(f"  - {d['name']}{ep}: `{d['path']}`")
        lines.append(f"**Datasets** ({len(datasets)}):")
        lines.extend(ds_lines)
    else:
        lines.append("**Datasets**: None — user needs to import data first")

    # Models
    models = store.list_models(project_id=project_id)
    if models:
        m_lines = []
        for m in models[:5]:
            step = f" (step {m['step']})" if m.get("step") else ""
            m_lines.append(f"  - {m['name']}{step}: `{m['path']}`")
        lines.append(f"**Models** ({len(models)}):")
        lines.extend(m_lines)
    else:
        lines.append("**Models**: None — user needs to train or register a model")

    # Active runs
    active_runs = store.get_active_runs()
    project_active = [r for r in active_runs if r.get("project_id") == project_id]
    if project_active:
        r_lines = []
        for r in project_active:
            r_lines.append(f"  - {r['run_type']} ({r['id'][:8]}): {r['status']}")
        lines.append(f"**Active Runs** ({len(project_active)}):")
        lines.extend(r_lines)
    else:
        lines.append("**Active Runs**: None")

    # Server status
    try:
        server_info = server_manager.server_info()
        if server_info.get("status") == "running":
            lines.append(
                f"**Server**: Running on port {server_info['port']} "
                f"(model: `{server_info['model_path']}`)"
            )
        else:
            lines.append("**Server**: Stopped")
    except Exception:
        lines.append("**Server**: Unknown")

    # Pipeline progress hint
    pipeline_hint = _derive_pipeline_hint(datasets, models, project_active, current_page)
    if pipeline_hint:
        lines.append(f"\n**Suggested Next Step**: {pipeline_hint}")

    return "\n".join(lines)


def _build_environment_context() -> list[str]:
    """Build environment/GPU context lines."""
    lines = []

    # RunPod detection
    pod_id = os.environ.get("RUNPOD_POD_ID", "")
    if pod_id:
        lines.append(f"**Environment**: RunPod GPU Pod (`{pod_id}`)")
    else:
        lines.append("**Environment**: Local")

    # GPU info from nvidia-smi
    gpus = get_gpu_info()
    if gpus:
        for i, g in enumerate(gpus):
            vram = f"{g['memory_used_mb']:.0f}/{g['memory_total_mb']:.0f} MB"
            lines.append(
                f"**GPU {i}**: {g['name']} — {g['utilization_pct']:.0f}% util, "
                f"{vram} VRAM, {g['temperature_c']:.0f}°C"
            )
    else:
        lines.append("**GPU**: Not detected")

    return lines


def _derive_pipeline_hint(
    datasets: list[dict],
    models: list[dict],
    active_runs: list[dict],
    current_page: str = "datasets",
) -> str:
    """Suggest the next logical step based on current state and page context."""
    # Page-specific hints take priority when they match the user's current stage
    if current_page == "datasets":
        if not datasets:
            return "Import a dataset — the user is on the Datasets page ready to add data"
        return "Data is available — compute statistics if not done, or explore episodes"
    if current_page == "training":
        if not datasets:
            return "No datasets yet — switch to Datasets to import data before training"
        if any(r["run_type"] in ("training", "rl_training") and r["status"] == "running" for r in active_runs):
            return "Training is in progress — monitor the run or wait for completion"
        return "Ready to train — configure and launch a GR00T finetune or Isaac Lab RL run"
    if current_page == "simulation":
        if models:
            return "Run simulation eval or open-loop evaluation on trained models"
        return "No models yet — train a model first, then return here to evaluate"
    if current_page == "models":
        if models:
            return "Optimize (ONNX/TensorRT), benchmark, or deploy a model"
        return "No models yet — train and register a model first"

    # Fallback: generic pipeline hint
    if not datasets:
        return "Import a dataset (Datasets stage)"
    if not models and not any(r["run_type"] in ("training", "rl_training") for r in active_runs):
        return "Start training (Training stage) — or compute statistics first if not done"
    if any(r["run_type"] in ("training", "rl_training") and r["status"] == "running" for r in active_runs):
        return "Training is in progress — monitor the run or wait for completion"
    if models and not any(r["run_type"] in ("evaluation", "simulation") for r in active_runs):
        return "Run simulation eval (Simulation stage)"
    if models:
        return "Register and deploy model (Models stage)"
    return ""
