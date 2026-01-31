"""System tools — GPU status, server status, active runs, embodiment config."""

from __future__ import annotations

import json
import traceback

from frontend.constants import EMBODIMENT_CHOICES
from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolResult, json_output
from frontend.services.gpu_monitor import get_gpu_info


def _get_gpu_status(ctx: ToolContext, args: dict) -> ToolResult:
    gpus = get_gpu_info()
    if not gpus:
        return ToolResult(output="No GPUs detected (nvidia-smi unavailable).")
    rows = []
    for i, g in enumerate(gpus):
        rows.append({
            "gpu": i,
            "name": g["name"],
            "utilization_pct": g["utilization_pct"],
            "memory_used_mb": g["memory_used_mb"],
            "memory_total_mb": g["memory_total_mb"],
            "temperature_c": g["temperature_c"],
            "power_w": g["power_w"],
        })
    return ToolResult(output=json_output(rows))


def _get_server_status(ctx: ToolContext, args: dict) -> ToolResult:
    info = ctx.server_manager.server_info()
    return ToolResult(output=json_output(info))


def _get_active_runs(ctx: ToolContext, args: dict) -> ToolResult:
    runs = ctx.store.get_active_runs()
    if not runs:
        return ToolResult(output="No active runs.")
    rows = []
    for r in runs:
        rows.append({
            "id": r["id"],
            "type": r["run_type"],
            "status": r["status"],
            "started": r.get("started_at", ""),
        })
    return ToolResult(output=json_output(rows))


def _get_embodiment_config(ctx: ToolContext, args: dict) -> ToolResult:
    tag = args.get("embodiment_tag", "new_embodiment")
    try:
        import sys
        sys.path.insert(0, ctx.project_root)
        from gr00t.configs.data.embodiment_configs import MODALITY_CONFIGS
        from gr00t.data.utils import to_json_serializable

        cfg = MODALITY_CONFIGS.get(tag)
        if cfg is None:
            return ToolResult(output=f"No config found for embodiment '{tag}'.", is_error=True)
        serializable = {}
        for modality, mc in cfg.items():
            serializable[modality] = to_json_serializable(mc)
        return ToolResult(output=json_output(serializable))
    except Exception as exc:
        return ToolResult(output=f"Error loading config: {exc}", is_error=True)


SYSTEM_TOOLS = [
    ToolDef(
        name="get_gpu_status",
        description="Get current GPU utilization, VRAM usage, temperature, and power draw.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_get_gpu_status,
        category="system",
    ),
    ToolDef(
        name="get_server_status",
        description="Get the inference server status including model, embodiment, port, and health.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_get_server_status,
        category="system",
    ),
    ToolDef(
        name="get_active_runs",
        description="Get all currently running or pending tasks (training, evaluation, etc.).",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_get_active_runs,
        category="system",
    ),
    ToolDef(
        name="get_embodiment_config",
        description="Get the modality configuration for a specific robot embodiment.",
        parameters={
            "type": "object",
            "properties": {
                "embodiment_tag": {
                    "type": "string",
                    "description": "Embodiment tag to look up",
                    "enum": EMBODIMENT_CHOICES,
                },
            },
            "required": ["embodiment_tag"],
        },
        handler=_get_embodiment_config,
        category="system",
    ),
]
