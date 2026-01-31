"""Evaluation tools — open-loop eval, simulation, task listing, results."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from frontend.constants import EMBODIMENT_CHOICES, SIM_TASKS
from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolResult, json_output


def _run_open_loop_eval(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    dataset_path = args.get("dataset_path", "").strip()
    model_path = args.get("model_path", "").strip()
    embodiment = args.get("embodiment_tag", "new_embodiment")
    traj_ids_str = args.get("traj_ids", "0")

    if not dataset_path:
        return ToolResult(output="dataset_path is required.", is_error=True)

    config = {
        "dataset_path": dataset_path,
        "model_path": model_path,
        "embodiment_tag": embodiment,
        "traj_ids": traj_ids_str,
    }
    run_id = ctx.store.create_run(project_id=pid, run_type="evaluation", config=config)

    eval_base = os.path.join(
        os.environ.get("WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio")),
        "eval_outputs",
    )
    save_dir = os.path.join(eval_base, run_id)
    os.makedirs(save_dir, exist_ok=True)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "-m", "gr00t.eval.open_loop_eval",
        "--dataset_path", dataset_path,
        "--embodiment_tag", embodiment,
        "--save_plot_path", f"{save_dir}/traj.jpeg",
    ]

    try:
        ids = [int(x.strip()) for x in traj_ids_str.split(",") if x.strip()]
        for tid in ids:
            cmd.extend(["--traj_ids", str(tid)])
    except ValueError:
        return ToolResult(output="Invalid trajectory IDs.", is_error=True)

    if model_path:
        cmd.extend(["--model_path", model_path])

    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"Open-loop evaluation launched.\nRun ID: {run_id}\n{msg}")


def _launch_simulation(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    task = args.get("task", "").strip()
    model_path = args.get("model_path", "").strip()
    if not task:
        return ToolResult(output="task is required.", is_error=True)
    if not model_path:
        return ToolResult(output="model_path is required.", is_error=True)

    n_episodes = int(args.get("n_episodes", 10))

    config = {"task": task, "model_path": model_path, "n_episodes": n_episodes}
    run_id = ctx.store.create_run(project_id=pid, run_type="simulation", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "-m", "gr00t.eval.rollout_policy",
        "--env_name", task,
        "--model_path", model_path,
        "--n_episodes", str(n_episodes),
    ]

    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"Simulation launched.\nRun ID: {run_id}\nTask: {task}\n{msg}")


def _list_simulation_tasks(ctx: ToolContext, args: dict) -> ToolResult:
    env_filter = args.get("environment")
    if env_filter:
        tasks = SIM_TASKS.get(env_filter, [])
        return ToolResult(output=json_output({env_filter: tasks}))
    return ToolResult(output=json_output(SIM_TASKS))


def _get_evaluation_results(ctx: ToolContext, args: dict) -> ToolResult:
    run_id = args.get("run_id", "").strip()
    if not run_id:
        return ToolResult(output="run_id is required.", is_error=True)

    status = ctx.task_runner.status(run_id)
    log = ctx.task_runner.tail_log(run_id, 200)

    result: dict = {"run_id": run_id, "status": status}

    # Parse MSE/MAE metrics
    metrics = []
    for line in log.splitlines():
        m = re.search(r"MSE for trajectory (\d+): ([\d.e+-]+), MAE: ([\d.e+-]+)", line)
        if m:
            metrics.append({
                "trajectory": int(m.group(1)),
                "mse": float(m.group(2)),
                "mae": float(m.group(3)),
            })
    if metrics:
        result["metrics"] = metrics

    # Parse success rate
    m = re.search(r"success rate:\s*([\d.]+)", log)
    if m:
        result["success_rate"] = float(m.group(1))

    return ToolResult(output=json_output(result))


EVAL_TOOLS = [
    ToolDef(
        name="run_open_loop_eval",
        description="Run open-loop evaluation comparing predicted vs ground-truth actions on a dataset.",
        parameters={
            "type": "object",
            "properties": {
                "dataset_path": {"type": "string", "description": "Path to the evaluation dataset"},
                "model_path": {"type": "string", "description": "Path to the model to evaluate"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag", "enum": EMBODIMENT_CHOICES},
                "traj_ids": {"type": "string", "description": "Comma-separated trajectory IDs to evaluate", "default": "0"},
            },
            "required": ["dataset_path"],
        },
        handler=_run_open_loop_eval,
        category="eval",
    ),
    ToolDef(
        name="launch_simulation",
        description="Launch a simulation evaluation (LIBERO, SimplerEnv, or BEHAVIOR).",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Full task name (e.g., libero/libero_panda/KITCHEN_SCENE1_...)"},
                "model_path": {"type": "string", "description": "Path to the model"},
                "n_episodes": {"type": "integer", "description": "Number of episodes to run", "default": 10},
            },
            "required": ["task", "model_path"],
        },
        handler=_launch_simulation,
        category="eval",
    ),
    ToolDef(
        name="list_simulation_tasks",
        description="List available simulation tasks for each environment.",
        parameters={
            "type": "object",
            "properties": {
                "environment": {"type": "string", "description": "Filter by environment", "enum": ["LIBERO", "SimplerEnv", "BEHAVIOR"]},
            },
            "required": [],
        },
        handler=_list_simulation_tasks,
        category="eval",
    ),
    ToolDef(
        name="get_evaluation_results",
        description="Get the results and metrics of a completed evaluation run.",
        parameters={
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "The evaluation run ID"},
            },
            "required": ["run_id"],
        },
        handler=_get_evaluation_results,
        category="eval",
    ),
]
