"""Training tools — launch, stop, status, checkpoint registration."""

from __future__ import annotations

import json
import re
from pathlib import Path

from frontend.constants import EMBODIMENT_CHOICES, TRAINING_PRESETS
from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolResult, json_output


def _launch_training(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    dataset_path = args.get("dataset_path", "").strip()
    if not dataset_path:
        return ToolResult(output="dataset_path is required.", is_error=True)

    # Load preset or use provided values
    preset_name = args.get("preset")
    if preset_name and preset_name in TRAINING_PRESETS:
        defaults = TRAINING_PRESETS[preset_name]
    else:
        defaults = TRAINING_PRESETS["Quick Start"]

    base_model = args.get("base_model", "nvidia/GR00T-N1.6-3B")
    embodiment = args.get("embodiment_tag", "new_embodiment")
    lr = args.get("learning_rate", defaults["learning_rate"])
    max_steps = int(args.get("max_steps", defaults["max_steps"]))
    batch_size = int(args.get("global_batch_size", defaults["global_batch_size"]))
    weight_decay = args.get("weight_decay", defaults["weight_decay"])
    warmup_ratio = args.get("warmup_ratio", defaults["warmup_ratio"])
    save_steps = int(args.get("save_steps", defaults["save_steps"]))
    output_dir = args.get("output_dir", "./outputs")

    config = {
        "base_model": base_model,
        "dataset_path": dataset_path,
        "embodiment_tag": embodiment,
        "learning_rate": lr,
        "max_steps": max_steps,
        "global_batch_size": batch_size,
        "weight_decay": weight_decay,
        "warmup_ratio": warmup_ratio,
        "save_steps": save_steps,
        "output_dir": output_dir,
    }

    run_id = ctx.store.create_run(project_id=pid, run_type="training", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "-m", "gr00t.experiment.launch_finetune",
        "--base_model_path", base_model,
        "--dataset_path", dataset_path,
        "--embodiment_tag", embodiment,
        "--learning_rate", str(lr),
        "--max_steps", str(max_steps),
        "--global_batch_size", str(batch_size),
        "--weight_decay", str(weight_decay),
        "--warmup_ratio", str(warmup_ratio),
        "--save_steps", str(save_steps),
        "--output_dir", output_dir,
    ]

    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)

    return ToolResult(
        output=(
            f"Training launched.\n"
            f"Run ID: {run_id}\n"
            f"Dataset: {dataset_path}\n"
            f"Max Steps: {max_steps}\n"
            f"Batch Size: {batch_size}\n"
            f"Learning Rate: {lr}\n"
            f"{msg}"
        )
    )


def _stop_training(ctx: ToolContext, args: dict) -> ToolResult:
    run_id = args.get("run_id", "").strip()
    if not run_id:
        return ToolResult(output="run_id is required.", is_error=True)
    msg = ctx.task_runner.stop(run_id)
    return ToolResult(output=msg)


def _get_run_status(ctx: ToolContext, args: dict) -> ToolResult:
    run_id = args.get("run_id", "").strip()
    if not run_id:
        return ToolResult(output="run_id is required.", is_error=True)

    status = ctx.task_runner.status(run_id)
    log = ctx.task_runner.tail_log(run_id, 30)

    # Parse latest metrics from log
    metrics = {}
    for line in log.splitlines():
        m = re.search(r"'loss':\s*([\d.e+-]+).*'step':\s*(\d+)", line)
        if m:
            metrics["loss"] = float(m.group(1))
            metrics["step"] = int(m.group(2))

    result = {"run_id": run_id, "status": status, "latest_metrics": metrics}

    # Parse checkpoints
    checkpoints = []
    for line in log.splitlines():
        m = re.search(r"Saving model checkpoint to (.+?)(?:\s|$)", line)
        if m:
            ckpt = m.group(1).strip()
            step_m = re.search(r"checkpoint-(\d+)", ckpt)
            checkpoints.append({"path": ckpt, "step": int(step_m.group(1)) if step_m else None})
    if checkpoints:
        result["checkpoints"] = checkpoints

    return ToolResult(output=json_output(result))


def _register_checkpoint(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    path = args.get("checkpoint_path", "").strip()
    name = args.get("model_name", "").strip()
    if not path or not name:
        return ToolResult(output="Both checkpoint_path and model_name are required.", is_error=True)

    step_m = re.search(r"checkpoint-(\d+)", path)
    step = int(step_m.group(1)) if step_m else None

    project = ctx.store.get_project(pid)
    mid = ctx.store.register_model(
        project_id=pid,
        name=name,
        path=path,
        embodiment_tag=project["embodiment_tag"] if project else "new_embodiment",
        step=step,
        base_model=project["base_model"] if project else "nvidia/GR00T-N1.6-3B",
    )
    return ToolResult(output=f"Model registered.\nID: {mid}\nName: {name}\nStep: {step}")


TRAIN_TOOLS = [
    ToolDef(
        name="launch_training",
        description="Launch a fine-tuning training run on the GR00T N1.6 model.",
        parameters={
            "type": "object",
            "properties": {
                "dataset_path": {"type": "string", "description": "Path to the training dataset"},
                "preset": {"type": "string", "description": "Training preset name", "enum": list(TRAINING_PRESETS.keys())},
                "base_model": {"type": "string", "description": "Base model path"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag", "enum": EMBODIMENT_CHOICES},
                "learning_rate": {"type": "number", "description": "Learning rate"},
                "max_steps": {"type": "integer", "description": "Maximum training steps"},
                "global_batch_size": {"type": "integer", "description": "Global batch size"},
                "output_dir": {"type": "string", "description": "Output directory for checkpoints"},
            },
            "required": ["dataset_path"],
        },
        handler=_launch_training,
        category="train",
    ),
    ToolDef(
        name="stop_training",
        description="Stop an active training run. WARNING: This will terminate the training process.",
        parameters={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "The run ID to stop"},
            },
            "required": ["run_id"],
        },
        handler=_stop_training,
        category="train",
    ),
    ToolDef(
        name="get_run_status",
        description="Get the status, latest metrics, and checkpoints of a run.",
        parameters={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "The run ID to check"},
            },
            "required": ["run_id"],
        },
        handler=_get_run_status,
        category="train",
    ),
    ToolDef(
        name="register_checkpoint",
        description="Register a training checkpoint as a named model in the model registry.",
        parameters={
            "type": "object",
            "properties": {
                "checkpoint_path": {"type": "string", "description": "Path to the checkpoint directory"},
                "model_name": {"type": "string", "description": "Name for the registered model"},
            },
            "required": ["checkpoint_path", "model_name"],
        },
        handler=_register_checkpoint,
        category="train",
    ),
]
