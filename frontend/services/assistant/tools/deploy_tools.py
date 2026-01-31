"""Deploy tools — model registration, server deployment, optimization, benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from frontend.constants import EMBODIMENT_CHOICES
from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolResult, json_output


def _register_model(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    name = args.get("name", "").strip()
    path = args.get("path", "").strip()
    if not name or not path:
        return ToolResult(output="Both name and path are required.", is_error=True)

    embodiment = args.get("embodiment_tag", "new_embodiment")
    step = args.get("step")
    base_model = args.get("base_model", "nvidia/GR00T-N1.6-3B")

    mid = ctx.store.register_model(
        project_id=pid,
        name=name,
        path=path,
        base_model=base_model,
        embodiment_tag=embodiment,
        step=int(step) if step is not None else None,
    )
    return ToolResult(output=f"Model registered.\nID: {mid}\nName: {name}\nPath: {path}")


def _deploy_server(ctx: ToolContext, args: dict) -> ToolResult:
    model_path = args.get("model_path", "").strip()
    if not model_path:
        return ToolResult(output="model_path is required.", is_error=True)

    embodiment = args.get("embodiment_tag", "new_embodiment")
    port = int(args.get("port", 5555))

    msg = ctx.server_manager.start(model_path, embodiment, port=port)
    return ToolResult(output=f"Server deployment initiated.\n{msg}")


def _stop_server(ctx: ToolContext, args: dict) -> ToolResult:
    msg = ctx.server_manager.stop()
    return ToolResult(output=msg)


def _export_onnx(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    model_path = args.get("model_path", "").strip()
    dataset_path = args.get("dataset_path", "").strip()
    output_dir = args.get("output_dir", "").strip()
    embodiment = args.get("embodiment_tag", "new_embodiment")

    if not model_path or not dataset_path or not output_dir:
        return ToolResult(output="model_path, dataset_path, and output_dir are all required.", is_error=True)

    config = {
        "model_path": model_path,
        "dataset_path": dataset_path,
        "embodiment_tag": embodiment,
        "output_dir": output_dir,
    }
    run_id = ctx.store.create_run(project_id=pid, run_type="onnx_export", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "scripts/deployment/export_onnx_n1d6.py",
        "--model_path", model_path,
        "--dataset_path", dataset_path,
        "--embodiment_tag", embodiment,
        "--output_dir", output_dir,
    ]

    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"ONNX export launched.\nRun ID: {run_id}\n{msg}")


def _build_tensorrt(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    onnx_path = args.get("onnx_path", "").strip()
    precision = args.get("precision", "bf16")

    if not onnx_path:
        return ToolResult(output="onnx_path is required.", is_error=True)

    engine_path = onnx_path.replace(".onnx", f".{precision}.trt")
    config = {"onnx_path": onnx_path, "engine_path": engine_path, "precision": precision}
    run_id = ctx.store.create_run(project_id=pid, run_type="tensorrt_build", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "scripts/deployment/build_tensorrt_engine.py",
        "--onnx", onnx_path,
        "--engine", engine_path,
        "--precision", precision,
    ]

    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"TensorRT build launched.\nRun ID: {run_id}\nEngine: {engine_path}\n{msg}")


def _run_benchmark(ctx: ToolContext, args: dict) -> ToolResult:
    pid = ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected.", is_error=True)

    model_path = args.get("model_path", "").strip()
    embodiment = args.get("embodiment_tag", "new_embodiment")
    num_iters = int(args.get("num_iterations", 100))

    if not model_path:
        return ToolResult(output="model_path is required.", is_error=True)

    config = {"model_path": model_path, "embodiment_tag": embodiment, "num_iterations": num_iters}
    run_id = ctx.store.create_run(project_id=pid, run_type="benchmark", config=config)

    venv_python = str(Path(ctx.project_root) / ".venv" / "bin" / "python")
    cmd = [
        venv_python, "scripts/deployment/benchmark_inference.py",
        "--model_path", model_path,
        "--embodiment_tag", embodiment,
        "--num_iterations", str(num_iters),
    ]

    trt_path = args.get("trt_engine_path", "").strip()
    if trt_path:
        cmd.extend(["--trt_engine_path", trt_path])

    msg = ctx.task_runner.launch(run_id, cmd, cwd=ctx.project_root)
    return ToolResult(output=f"Benchmark launched.\nRun ID: {run_id}\n{msg}")


DEPLOY_TOOLS = [
    ToolDef(
        name="register_model",
        description="Register a model (checkpoint or pretrained) in the model registry.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Model name"},
                "path": {"type": "string", "description": "Path to the model/checkpoint"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag", "enum": EMBODIMENT_CHOICES},
                "step": {"type": "integer", "description": "Training step (if from checkpoint)"},
                "base_model": {"type": "string", "description": "Base model it was fine-tuned from"},
            },
            "required": ["name", "path"],
        },
        handler=_register_model,
        category="deploy",
    ),
    ToolDef(
        name="deploy_server",
        description="Deploy a model to the GR00T inference server.",
        parameters={
            "type": "object",
            "properties": {
                "model_path": {"type": "string", "description": "Path to the model to deploy"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag", "enum": EMBODIMENT_CHOICES},
                "port": {"type": "integer", "description": "Server port", "default": 5555},
            },
            "required": ["model_path"],
        },
        handler=_deploy_server,
        category="deploy",
    ),
    ToolDef(
        name="stop_server",
        description="Stop the running inference server.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_stop_server,
        category="deploy",
    ),
    ToolDef(
        name="export_onnx",
        description="Export a model to ONNX format for optimization.",
        parameters={
            "type": "object",
            "properties": {
                "model_path": {"type": "string", "description": "Model path"},
                "dataset_path": {"type": "string", "description": "Dataset path for shape inference"},
                "output_dir": {"type": "string", "description": "Output directory for ONNX file"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag", "enum": EMBODIMENT_CHOICES},
            },
            "required": ["model_path", "dataset_path", "output_dir"],
        },
        handler=_export_onnx,
        category="deploy",
    ),
    ToolDef(
        name="build_tensorrt",
        description="Build a TensorRT engine from an ONNX model for optimized inference.",
        parameters={
            "type": "object",
            "properties": {
                "onnx_path": {"type": "string", "description": "Path to the ONNX model"},
                "precision": {"type": "string", "description": "Precision mode", "enum": ["bf16", "fp16", "fp32"]},
            },
            "required": ["onnx_path"],
        },
        handler=_build_tensorrt,
        category="deploy",
    ),
    ToolDef(
        name="run_benchmark",
        description="Run inference benchmarks to measure latency and throughput.",
        parameters={
            "type": "object",
            "properties": {
                "model_path": {"type": "string", "description": "Model path to benchmark"},
                "embodiment_tag": {"type": "string", "description": "Embodiment tag", "enum": EMBODIMENT_CHOICES},
                "num_iterations": {"type": "integer", "description": "Number of benchmark iterations", "default": 100},
                "trt_engine_path": {"type": "string", "description": "Optional TensorRT engine path"},
            },
            "required": ["model_path"],
        },
        handler=_run_benchmark,
        category="deploy",
    ),
]
