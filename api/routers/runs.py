"""Run management endpoints — launch, poll, stop."""

from __future__ import annotations

import glob as glob_mod
import json
import logging
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.auth import require_auth
from api.deps import get_project_root, get_store, get_task_runner, validate_path_param
from api.schemas.datasets import RunCreate, RunList, RunResponse, RunStatusResponse
from api.schemas.models import BenchmarkMetricsResponse, BenchmarkRow
from api.schemas.simulation import (
    ArtifactItem,
    ArtifactList,
    EvalMetric,
    EvalMetricsResponse,
    SimMetric,
)
from api.schemas.training import (
    CheckpointInfo,
    LossPoint,
    TrainingMetricsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/runs",
    tags=["runs"],
    dependencies=[Depends(require_auth)],
)


def _build_cmd(run_type: str, config: dict, project_root: str) -> list[str]:
    """Build the subprocess command for a given run type."""
    venv_python = os.path.join(project_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        import sys

        venv_python = sys.executable

    if run_type == "stats_computation":
        dataset_path = config.get("dataset_path", "")
        embodiment_tag = config.get("embodiment_tag", "new_embodiment")
        return [
            venv_python,
            "-m",
            "gr00t.data.stats",
            "--dataset-path",
            dataset_path,
            "--embodiment-tag",
            embodiment_tag,
        ]

    if run_type == "conversion":
        repo_id = config.get("repo_id", "")
        output_dir = config.get("output_dir", "")
        return [
            venv_python,
            "scripts/lerobot_conversion/convert_v3_to_v2.py",
            "--repo-id",
            repo_id,
            "--root",
            output_dir,
        ]

    if run_type == "training":
        return _build_training_cmd(config, venv_python)

    if run_type == "simulation":
        return _build_simulation_cmd(config, venv_python)

    if run_type == "evaluation":
        return _build_evaluation_cmd(config, venv_python)

    if run_type == "onnx_export":
        return _build_onnx_export_cmd(config, venv_python)

    if run_type == "tensorrt_build":
        return _build_tensorrt_cmd(config, venv_python)

    if run_type == "benchmark":
        return _build_benchmark_cmd(config, venv_python)

    if run_type == "rl_training":
        raise HTTPException(
            status_code=400,
            detail="Isaac Lab RL training is not yet available",
        )

    raise HTTPException(status_code=400, detail=f"Unknown run type: {run_type}")


def _build_simulation_cmd(config: dict, venv_python: str) -> list[str]:
    """Build Isaac Sim rollout command from config dict.

    Port of frontend/pages/simulation.py:launch_sim().
    """
    task = config.get("task", "")
    model_path = config.get("model_path", "")
    if "|" in model_path:
        model_path = model_path.split("|")[-1].strip()

    cmd = [
        venv_python, "-m", "gr00t.eval.rollout_policy",
        "--env_name", task,
        "--max_episode_steps", str(int(config.get("max_steps", 504))),
        "--n_action_steps", str(int(config.get("n_action_steps", 8))),
        "--n_episodes", str(int(config.get("n_episodes", 10))),
        "--n_envs", str(int(config.get("n_envs", 1))),
    ]

    use_server = config.get("use_server", False)
    if use_server:
        cmd.extend([
            "--policy_client_host", config.get("server_host", "localhost"),
            "--policy_client_port", str(int(config.get("server_port", 5555))),
        ])
    elif model_path.strip():
        cmd.extend(["--model_path", model_path.strip()])

    return cmd


def _build_evaluation_cmd(config: dict, venv_python: str) -> list[str]:
    """Build open-loop eval command from config dict.

    Port of frontend/pages/simulation.py:launch_open_loop().
    """
    dataset_path = config.get("dataset_path", "")
    model_path = config.get("model_path", "")
    if "|" in model_path:
        model_path = model_path.split("|")[-1].strip()

    embodiment = config.get("embodiment_tag", "new_embodiment")
    save_plot_path = config.get("save_plot_path", "")

    cmd = [
        venv_python, "-m", "gr00t.eval.open_loop_eval",
        "--dataset_path", dataset_path,
        "--embodiment_tag", embodiment,
        "--steps", str(int(config.get("steps", 200))),
        "--action_horizon", str(int(config.get("action_horizon", 16))),
    ]

    if save_plot_path:
        cmd.extend(["--save_plot_path", save_plot_path])

    # Trajectory IDs
    traj_ids_str = config.get("traj_ids", "0")
    try:
        ids = [int(x.strip()) for x in str(traj_ids_str).split(",") if x.strip()]
        for tid in ids:
            cmd.extend(["--traj_ids", str(tid)])
    except ValueError:
        pass

    if model_path.strip():
        cmd.extend(["--model_path", model_path.strip()])

    return cmd


def _build_onnx_export_cmd(config: dict, venv_python: str) -> list[str]:
    """Build ONNX export command from config dict."""
    model_path = config.get("model_path", "")
    dataset_path = config.get("dataset_path", "")
    embodiment = config.get("embodiment_tag", "new_embodiment")
    output_dir = config.get("output_dir", "")

    return [
        venv_python, "scripts/deployment/export_onnx_n1d6.py",
        "--model_path", model_path,
        "--dataset_path", dataset_path,
        "--embodiment_tag", embodiment,
        "--output_dir", output_dir,
    ]


def _build_tensorrt_cmd(config: dict, venv_python: str) -> list[str]:
    """Build TensorRT engine build command from config dict."""
    onnx_path = config.get("onnx_path", "")
    engine_path = config.get("engine_path", "")
    precision = config.get("precision", "bf16")

    return [
        venv_python, "scripts/deployment/build_tensorrt_engine.py",
        "--onnx", onnx_path,
        "--engine", engine_path,
        "--precision", precision,
    ]


def _build_benchmark_cmd(config: dict, venv_python: str) -> list[str]:
    """Build benchmark inference command from config dict."""
    model_path = config.get("model_path", "")
    embodiment = config.get("embodiment_tag", "new_embodiment")
    num_iters = int(config.get("num_iterations", 100))

    cmd = [
        venv_python, "scripts/deployment/benchmark_inference.py",
        "--model_path", model_path,
        "--embodiment_tag", embodiment,
        "--num_iterations", str(num_iters),
    ]

    trt_path = config.get("trt_engine_path")
    if trt_path:
        cmd.extend(["--trt_engine_path", trt_path])

    if config.get("skip_compile"):
        cmd.append("--skip_compile")

    return cmd


def _parse_benchmark_table(log_text: str) -> list[BenchmarkRow]:
    """Parse benchmark log output into structured rows.

    Port of frontend/pages/models.py:_parse_benchmark_table().
    """
    results: list[BenchmarkRow] = []
    lines = log_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Device" in line and "Mode" in line and "E2E" in line and "|" in line:
            header_idx = i
            break
    if header_idx is None:
        return results
    header_line = lines[header_idx]
    headers = [h.strip() for h in header_line.strip().strip("|").split("|")]
    for line in lines[header_idx + 2:]:
        line = line.strip()
        if not line or not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= len(headers):
            row_dict = {}
            for j, h in enumerate(headers):
                row_dict[h] = cells[j] if j < len(cells) else ""
            results.append(BenchmarkRow(
                device=row_dict.get("Device", ""),
                mode=row_dict.get("Mode", ""),
                data_processing=row_dict.get("Data Processing", ""),
                backbone=row_dict.get("Backbone", ""),
                action_head=row_dict.get("Action Head", ""),
                e2e=row_dict.get("E2E", ""),
                frequency=row_dict.get("Frequency", ""),
            ))
    return results


def _get_eval_output_dir(run_id: str) -> str:
    """Return the eval output directory for a run."""
    base = os.path.join(
        os.environ.get("WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio")),
        "eval_outputs",
    )
    return os.path.join(base, run_id)


def _parse_eval_metrics(log_text: str) -> EvalMetricsResponse:
    """Parse evaluation log text into structured metrics."""
    sim_metrics: list[SimMetric] = []
    eval_metrics: list[EvalMetric] = []

    m = re.search(r"success rate:\s*([\d.]+)", log_text)
    if m:
        sim_metrics.append(SimMetric(name="Success Rate", value=m.group(1)))

    m = re.search(r"Collecting \d+ episodes took ([\d.]+) seconds", log_text)
    if m:
        sim_metrics.append(SimMetric(name="Total Time (s)", value=m.group(1)))

    for line in log_text.splitlines():
        m = re.search(r"MSE for trajectory (\d+): ([\d.e+-]+), MAE: ([\d.e+-]+)", line)
        if m:
            eval_metrics.append(EvalMetric(
                trajectory=int(m.group(1)),
                mse=float(m.group(2)),
                mae=float(m.group(3)),
            ))

    return EvalMetricsResponse(sim_metrics=sim_metrics, eval_metrics=eval_metrics)


def _build_training_cmd(config: dict, venv_python: str) -> list[str]:
    """Build the training subprocess command from config dict.

    Port of frontend/pages/training.py:_build_training_cmd().
    """
    dataset_path = config.get("dataset_path", "")
    base_model = config.get("base_model", "nvidia/GR00T-N1.6-3B")
    embodiment = config.get("embodiment_tag", "new_embodiment")

    # Extract path from "name | path" dropdown format
    if "|" in dataset_path:
        dataset_path = dataset_path.split("|")[-1].strip()
    if "|" in base_model:
        base_model = base_model.split("|")[-1].strip()

    cmd = [
        venv_python, "-m", "gr00t.experiment.launch_finetune",
        "--base_model_path", base_model,
        "--dataset_path", dataset_path,
        "--embodiment_tag", embodiment,
        "--learning_rate", str(config.get("learning_rate", 1e-4)),
        "--max_steps", str(int(config.get("max_steps", 10000))),
        "--global_batch_size", str(int(config.get("global_batch_size", 64))),
        "--weight_decay", str(config.get("weight_decay", 1e-5)),
        "--warmup_ratio", str(config.get("warmup_ratio", 0.05)),
        "--save_steps", str(int(config.get("save_steps", 1000))),
        "--shard_size", str(int(config.get("shard_size", 1024))),
        "--episode_sampling_rate", str(config.get("episode_sampling_rate", 0.1)),
        "--output_dir", config.get("output_dir", "./outputs"),
    ]

    # Tuning flags
    if config.get("tune_llm"):
        cmd.append("--tune_llm")
    if config.get("tune_visual"):
        cmd.append("--tune_visual")
    if not config.get("tune_projector", True):
        cmd.append("--no-tune_projector")
    if not config.get("tune_diffusion", True):
        cmd.append("--no-tune_diffusion_model")
    if config.get("use_wandb"):
        cmd.append("--use_wandb")

    # Distributed / advanced
    num_gpus = int(config.get("num_gpus", 1))
    cmd.extend(["--num_gpus", str(num_gpus)])
    cmd.extend(["--gradient_accumulation_steps", str(int(config.get("gradient_accumulation_steps", 1)))])
    cmd.extend(["--save_total_limit", str(int(config.get("save_total_limit", 5)))])
    cmd.extend(["--dataloader_num_workers", str(int(config.get("dataloader_num_workers", 4)))])

    deepspeed_stage = int(config.get("deepspeed_stage", 2))
    if deepspeed_stage != 2:
        cmd.extend(["--deepspeed_stage", str(deepspeed_stage)])
    if config.get("gradient_checkpointing"):
        cmd.append("--gradient_checkpointing")

    optimizer = config.get("optimizer", "adamw_torch_fused")
    if optimizer != "adamw_torch_fused":
        cmd.extend(["--optim", optimizer])

    lr_scheduler = config.get("lr_scheduler", "cosine")
    if lr_scheduler != "cosine":
        cmd.extend(["--lr_scheduler_type", lr_scheduler])

    # Image augmentation
    if config.get("color_jitter"):
        cmd.extend([
            "--color_jitter_params",
            "brightness", str(config.get("brightness", 0.3)),
            "contrast", str(config.get("contrast", 0.3)),
            "saturation", str(config.get("saturation", 0.3)),
            "hue", str(config.get("hue", 0.1)),
        ])
    rotation = int(config.get("random_rotation", 0))
    if rotation > 0:
        cmd.extend(["--random_rotation_angle", str(rotation)])

    state_dropout = float(config.get("state_dropout", 0))
    if state_dropout > 0:
        cmd.extend(["--state_dropout_prob", str(state_dropout)])
    if config.get("enable_profiling"):
        cmd.append("--enable_profiling")

    # Precision flags
    max_grad_norm = config.get("max_grad_norm")
    if max_grad_norm is not None:
        cmd.extend(["--max_grad_norm", str(max_grad_norm)])

    if config.get("bf16", True):
        cmd.append("--bf16")
    else:
        cmd.append("--no-bf16")

    if config.get("fp16", False):
        cmd.append("--fp16")
    else:
        cmd.append("--no-fp16")

    if config.get("tf32", True):
        cmd.append("--tf32")
    else:
        cmd.append("--no-tf32")

    # Evaluation
    if config.get("eval_enable"):
        cmd.extend([
            "--eval_strategy", "steps",
            "--eval_steps", str(int(config.get("eval_steps", 500))),
        ])
        eval_split = config.get("eval_split_ratio")
        if eval_split is not None:
            cmd.extend(["--eval_split_ratio", str(eval_split)])

    # Resume from checkpoint
    resume_ckpt = config.get("resume_checkpoint_path")
    if resume_ckpt:
        ckpt_parent = str(Path(resume_ckpt).parent)
        for i, arg in enumerate(cmd):
            if arg == "--output_dir" and i + 1 < len(cmd):
                cmd[i + 1] = ckpt_parent
                break

    return cmd


def _parse_training_metrics(
    log_text: str, max_steps: int, status: str,
) -> TrainingMetricsResponse:
    """Parse training log text into structured metrics."""
    steps: list[int] = []
    losses: list[float] = []
    checkpoints: list[CheckpointInfo] = []
    current_step = 0

    for line in log_text.splitlines():
        # Loss: {'loss': 0.1234, ..., 'step': 500}
        m = re.search(r"'loss':\s*([\d.e+-]+).*'step':\s*(\d+)", line)
        if m:
            losses.append(float(m.group(1)))
            step = int(m.group(2))
            steps.append(step)
            current_step = max(current_step, step)

        # Checkpoint: Saving model checkpoint to /path/to/checkpoint-5000
        m = re.search(r"Saving model checkpoint to (.+?)(?:\s|$)", line)
        if m:
            ckpt_path = m.group(1).strip()
            step_m = re.search(r"checkpoint-(\d+)", ckpt_path)
            checkpoints.append(CheckpointInfo(
                path=ckpt_path,
                step=int(step_m.group(1)) if step_m else None,
            ))

    loss_curve = [
        LossPoint(step=s, loss=l) for s, l in zip(steps, losses)
    ]
    progress_pct = (current_step / max_steps * 100) if max_steps > 0 else 0

    return TrainingMetricsResponse(
        loss_curve=loss_curve,
        checkpoints=checkpoints,
        current_step=current_step,
        max_steps=max_steps,
        progress_pct=min(progress_pct, 100.0),
        status=status,
    )


@router.get("", response_model=RunList)
async def list_runs(
    project_id: str | None = Query(None),
    run_type: str | None = Query(None),
    store=Depends(get_store),
) -> RunList:
    runs = store.list_runs(project_id=project_id, run_type=run_type)
    return RunList(runs=[RunResponse(**r) for r in runs])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    body: RunCreate,
    project_id: str = Query(...),
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
    project_root: str = Depends(get_project_root),
) -> RunResponse:
    # Validate project exists
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate user-supplied paths in the config
    config = dict(body.config)
    for path_key in ("dataset_path", "model_path", "output_dir", "onnx_path", "engine_path"):
        val = config.get(path_key, "")
        if val and isinstance(val, str):
            # Strip "name | path" dropdown format before validating
            raw = val.split("|")[-1].strip() if "|" in val else val
            if raw:
                validate_path_param(raw)

    # For evaluation runs, inject save_plot_path into config
    if body.run_type == "evaluation":
        save_dir = _get_eval_output_dir("")  # we need run_id first
        # We'll set it after creating the run

    # Create the run record
    run_id = store.create_run(
        project_id=project_id,
        run_type=body.run_type,
        config=config,
        dataset_id=body.dataset_id,
    )

    # For evaluation runs, create output dir and set save_plot_path
    if body.run_type == "evaluation":
        save_dir = _get_eval_output_dir(run_id)
        os.makedirs(save_dir, exist_ok=True)
        config["save_plot_path"] = os.path.join(save_dir, "traj.jpeg")

    # Build command and launch
    cmd = _build_cmd(body.run_type, config, project_root)
    task_runner.launch(run_id, cmd, cwd=project_root)

    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to create run")
    return RunResponse(**run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, store=Depends(get_store)) -> RunResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(**run)


@router.get("/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
) -> RunStatusResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    status = task_runner.status(run_id)
    log_tail = task_runner.tail_log(run_id, 80)
    return RunStatusResponse(status=status, log_tail=log_tail)


@router.get("/{run_id}/metrics", response_model=TrainingMetricsResponse)
async def get_run_metrics(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
) -> TrainingMetricsResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    status = task_runner.status(run_id)
    log_text = task_runner.tail_log(run_id, 500)

    # Get max_steps from run config
    max_steps = 10000
    try:
        config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
        max_steps = int(config.get("max_steps", 10000))
    except Exception:
        logger.debug("Failed to parse config for run %s", run_id, exc_info=True)

    return _parse_training_metrics(log_text, max_steps, status)


@router.post("/{run_id}/stop")
async def stop_run(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    msg = task_runner.stop(run_id)
    return {"message": msg}


@router.get("/{run_id}/eval-metrics", response_model=EvalMetricsResponse)
async def get_eval_metrics(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
) -> EvalMetricsResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    log_text = task_runner.tail_log(run_id, 500)
    return _parse_eval_metrics(log_text)


@router.get("/{run_id}/benchmark-metrics", response_model=BenchmarkMetricsResponse)
async def get_benchmark_metrics(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
) -> BenchmarkMetricsResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    status = task_runner.status(run_id)
    log_text = task_runner.tail_log(run_id, 200)
    rows = _parse_benchmark_table(log_text)
    return BenchmarkMetricsResponse(rows=rows, status=status)


@router.get("/{run_id}/artifacts", response_model=ArtifactList)
async def list_artifacts(
    run_id: str,
    store=Depends(get_store),
) -> ArtifactList:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    output_dir = _get_eval_output_dir(run_id)
    items: list[ArtifactItem] = []
    if os.path.isdir(output_dir):
        for ext in ("*.jpeg", "*.jpg", "*.png"):
            for fpath in sorted(glob_mod.glob(os.path.join(output_dir, ext))):
                fname = os.path.basename(fpath)
                items.append(ArtifactItem(
                    filename=fname,
                    url=f"/api/runs/{run_id}/artifacts/{fname}",
                ))
    return ArtifactList(artifacts=items)


@router.get("/{run_id}/artifacts/{filename}")
async def get_artifact(
    run_id: str,
    filename: str,
    store=Depends(get_store),
):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Prevent path traversal
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    output_dir = _get_eval_output_dir(run_id)
    file_path = os.path.join(output_dir, safe_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(file_path)
