from __future__ import annotations

"""Deploy tab — model registry, server deployment, ONNX/TensorRT optimization,
benchmark pipeline, and benchmark history dashboard."""

import json
from pathlib import Path

import gradio as gr

from frontend.services.server_manager import ServerManager
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


def _models_table(store: WorkspaceStore, project_id: str | None) -> list[list]:
    models = store.list_models(project_id=project_id)
    if not models:
        return [["No models registered", "", "", "", ""]]
    rows = []
    for m in models:
        evals = store.list_evaluations(model_id=m["id"])
        eval_summary = ""
        if evals:
            for ev in evals[:3]:
                try:
                    metrics = json.loads(ev["metrics"]) if isinstance(ev["metrics"], str) else ev["metrics"]
                    eval_summary += ", ".join(f"{k}={v}" for k, v in metrics.items())
                except Exception:
                    pass
        rows.append([
            m["name"],
            m["path"],
            str(m.get("step", "")),
            m.get("embodiment_tag", ""),
            eval_summary or "-",
        ])
    return rows


def _parse_benchmark_table(log_text: str) -> list[dict]:
    """Parse benchmark results from log output.

    Looks for table rows like:
    | Device | Mode | Data Processing | Backbone | Action Head | E2E | Frequency |
    """
    results = []
    lines = log_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Device" in line and "Mode" in line and "E2E" in line and "|" in line:
            header_idx = i
            break

    if header_idx is None:
        return results

    # Parse header
    header_line = lines[header_idx]
    headers = [h.strip() for h in header_line.strip().strip("|").split("|")]

    # Skip separator line
    for line in lines[header_idx + 2:]:
        line = line.strip()
        if not line or not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= len(headers):
            row = {}
            for j, h in enumerate(headers):
                row[h] = cells[j] if j < len(cells) else ""
            results.append(row)

    return results


def _benchmark_history_table(store: WorkspaceStore, project_id: str | None) -> list[list]:
    """Build benchmark history table from DB runs."""
    runs = store.list_runs(project_id=project_id, run_type="benchmark")
    if not runs:
        return [["No benchmark runs", "", "", "", ""]]
    rows = []
    for r in runs:
        metrics = {}
        try:
            if r.get("metrics"):
                metrics = json.loads(r["metrics"]) if isinstance(r["metrics"], str) else r["metrics"]
        except Exception:
            pass
        config = {}
        try:
            config = json.loads(r["config"]) if isinstance(r["config"], str) else r["config"]
        except Exception:
            pass
        model = config.get("model_path", "-")
        if len(model) > 30:
            model = "..." + model[-27:]
        mode = metrics.get("mode", "-")
        e2e = metrics.get("e2e_ms", "-")
        freq = metrics.get("frequency_hz", "-")
        started = r.get("started_at", "")[:16] if r.get("started_at") else ""
        rows.append([model, mode, str(e2e), str(freq), started])
    return rows


def create_deploy_tab(
    server_manager: ServerManager,
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
):
    with gr.Tab("Deploy"):
        gr.Markdown("## Deploy")

        # ── Model Registry ──
        gr.Markdown("### Model Registry")
        model_table = gr.Dataframe(
            headers=["Name", "Path", "Step", "Embodiment", "Eval Scores"],
            label="Registered Models",
            interactive=False,
            value=_models_table(store, None),
        )
        refresh_models_btn = gr.Button("Refresh", size="sm")

        gr.Markdown("---")

        # ── Register a model manually ──
        gr.Markdown("### Register Model")
        with gr.Row():
            reg_name = gr.Textbox(label="Name", placeholder="my-finetuned-v1")
            reg_path = gr.Textbox(
                label="Checkpoint Path",
                placeholder="/path/to/checkpoint-5000",
            )
        with gr.Row():
            reg_embodiment = gr.Dropdown(
                label="Embodiment Tag",
                choices=EMBODIMENT_CHOICES,
                value="new_embodiment",
            )
            reg_step = gr.Number(label="Step", value=0, precision=0)
            reg_base_model = gr.Textbox(
                label="Base Model", value="nvidia/GR00T-N1.6-3B"
            )
        register_btn = gr.Button("Register Model", variant="primary", size="sm")
        reg_status = gr.Textbox(label="Status", interactive=False)

        gr.Markdown("---")

        # ── Deploy to Server ──
        gr.Markdown("### Deploy to Server")
        deploy_model_path = gr.Textbox(
            label="Model Path to Deploy",
            placeholder="Paste a model path from the registry above",
        )
        with gr.Row():
            deploy_embodiment = gr.Dropdown(
                label="Embodiment Tag",
                choices=EMBODIMENT_CHOICES,
                value="new_embodiment",
            )
            deploy_port = gr.Number(label="Port", value=5555, precision=0)
        with gr.Row():
            deploy_btn = gr.Button("Deploy to Server", variant="primary", size="sm")
            undeploy_btn = gr.Button("Stop Server", variant="stop", size="sm")
        deploy_status = gr.Textbox(label="Deploy Status", interactive=False)

        gr.Markdown("---")

        # ── C1: Model Optimization Pipeline ──
        gr.Markdown("### Optimize Model")

        # Step 1: ONNX Export
        gr.Markdown("#### Step 1: Export to ONNX")
        with gr.Row():
            onnx_model_path = gr.Textbox(
                label="Model Path",
                placeholder="/path/to/model",
            )
            onnx_dataset_path = gr.Textbox(
                label="Dataset Path (for shape inference)",
                placeholder="/path/to/dataset",
            )
        with gr.Row():
            onnx_embodiment = gr.Dropdown(
                label="Embodiment Tag",
                choices=EMBODIMENT_CHOICES,
                value="new_embodiment",
            )
            onnx_output_dir = gr.Textbox(
                label="Output Dir",
                placeholder="/path/to/onnx_output",
            )
        onnx_export_btn = gr.Button("Export ONNX", variant="primary", size="sm")
        onnx_status = gr.Textbox(label="Status", interactive=False)
        onnx_log = gr.Textbox(label="Log Output", lines=8, interactive=False)
        onnx_run_id = gr.State(value="")

        gr.Markdown("---")

        # Step 2: TensorRT Build
        gr.Markdown("#### Step 2: Build TensorRT Engine")
        with gr.Row():
            trt_onnx_path = gr.Textbox(
                label="ONNX Path",
                placeholder="Auto-filled from Step 1, or enter manually",
            )
            trt_precision = gr.Dropdown(
                label="Precision",
                choices=["bf16", "fp16", "fp32"],
                value="bf16",
            )
        trt_build_btn = gr.Button("Build Engine", variant="primary", size="sm")
        trt_status = gr.Textbox(label="Status", interactive=False)
        trt_log = gr.Textbox(label="Log Output", lines=8, interactive=False)
        trt_run_id = gr.State(value="")

        gr.Markdown("---")

        # Step 3: Benchmark
        gr.Markdown("#### Step 3: Benchmark")
        with gr.Row():
            bench_model_path = gr.Textbox(
                label="Model Path",
                placeholder="/path/to/model",
            )
            bench_trt_path = gr.Textbox(
                label="TensorRT Engine Path (optional)",
                placeholder="Auto-filled from Step 2, or leave empty",
            )
        with gr.Row():
            bench_embodiment = gr.Dropdown(
                label="Embodiment Tag",
                choices=EMBODIMENT_CHOICES,
                value="new_embodiment",
            )
            bench_num_iters = gr.Number(label="Num Iterations", value=100, precision=0)
            bench_skip_compile = gr.Checkbox(label="Skip Compile", value=False)
        bench_run_btn = gr.Button("Run Benchmark", variant="primary", size="sm")
        bench_status = gr.Textbox(label="Status", interactive=False)
        bench_results = gr.Dataframe(
            headers=["Device", "Mode", "Data Processing", "Backbone", "Action Head", "E2E", "Frequency"],
            label="Benchmark Results",
            interactive=False,
        )
        bench_chart = gr.Plot(label="Timing Comparison")
        bench_run_id = gr.State(value="")

        gr.Markdown("---")

        # ── C2: Benchmark History Dashboard ──
        gr.Markdown("### Benchmark History")
        bench_history_refresh = gr.Button("Refresh", size="sm")
        bench_history_table = gr.Dataframe(
            headers=["Model", "Mode", "E2E (ms)", "Freq (Hz)", "Date"],
            label="Benchmark History",
            interactive=False,
            value=_benchmark_history_table(store, None),
        )
        bench_history_chart = gr.Plot(label="Frequency Comparison")

        gr.Markdown("---")

        # ── Export ──
        gr.Markdown("### Export")
        export_model_path = gr.Textbox(
            label="Model Path",
            placeholder="Path to the model checkpoint",
        )
        export_cmd = gr.Code(
            label="Server Launch Command",
            language="shell",
            interactive=False,
            lines=3,
        )
        gen_cmd_btn = gr.Button("Generate Command", size="sm")

        # ── Callbacks ──

        def refresh_models(proj):
            pid = proj.get("id") if proj else None
            return _models_table(store, pid)

        def register_model(name, path, embodiment, step, base_model, proj):
            if not name.strip() or not path.strip():
                return "Name and path are required"
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first"
            if not Path(path).exists():
                return f"Warning: path does not exist on disk: {path}"
            mid = store.register_model(
                project_id=pid,
                name=name,
                path=path,
                base_model=base_model,
                embodiment_tag=embodiment,
                step=int(step),
            )
            return f"Model registered: {mid}"

        def deploy_model(model_path, embodiment, port):
            if not model_path.strip():
                return "Model path is required"
            msg = server_manager.start(model_path, embodiment, port=int(port))
            return msg

        def undeploy():
            return server_manager.stop()

        def generate_command(model_path):
            if not model_path.strip():
                return ""
            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            return (
                f"{venv_python} -m gr00t.eval.run_gr00t_server "
                f"--model_path {model_path} "
                f"--embodiment_tag new_embodiment "
                f"--port 5555 --device cuda --host 0.0.0.0"
            )

        # ── C1: ONNX Export callbacks ──

        def launch_onnx_export(model_path, dataset_path, embodiment, output_dir, proj):
            if not model_path.strip():
                return "Model path is required", "", ""
            if not dataset_path.strip():
                return "Dataset path is required", "", ""
            if not output_dir.strip():
                return "Output dir is required", "", ""
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first", "", ""

            config = {
                "model_path": model_path,
                "dataset_path": dataset_path,
                "embodiment_tag": embodiment,
                "output_dir": output_dir,
            }
            run_id = store.create_run(
                project_id=pid,
                run_type="onnx_export",
                config=config,
            )

            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            cmd = [
                venv_python,
                "scripts/deployment/export_onnx_n1d6.py",
                "--model_path", model_path,
                "--dataset_path", dataset_path,
                "--embodiment_tag", embodiment,
                "--output_dir", output_dir,
            ]

            msg = task_runner.launch(run_id, cmd, cwd=project_root)
            return msg, run_id, ""

        def poll_onnx_status(run_id):
            if not run_id:
                return "", "", ""
            status = task_runner.status(run_id)
            log = task_runner.tail_log(run_id, 30)
            status_msg = f"Status: {status}"

            # Auto-fill ONNX path on completion
            onnx_path_update = gr.update()
            if status == "completed":
                run = store.get_run(run_id)
                if run:
                    try:
                        config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
                        output_dir = config.get("output_dir", "")
                        expected_onnx = str(Path(output_dir) / "dit_model.onnx")
                        onnx_path_update = gr.update(value=expected_onnx)
                        status_msg += f" — ONNX exported to {expected_onnx}"
                    except Exception:
                        pass

            return status_msg, log, onnx_path_update

        # ── C1: TensorRT Build callbacks ──

        def launch_trt_build(onnx_path, precision, proj):
            if not onnx_path.strip():
                return "ONNX path is required", "", ""
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first", "", ""

            engine_path = onnx_path.replace(".onnx", f".{precision}.trt")
            config = {
                "onnx_path": onnx_path,
                "engine_path": engine_path,
                "precision": precision,
            }
            run_id = store.create_run(
                project_id=pid,
                run_type="tensorrt_build",
                config=config,
            )

            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            cmd = [
                venv_python,
                "scripts/deployment/build_tensorrt_engine.py",
                "--onnx", onnx_path,
                "--engine", engine_path,
                "--precision", precision,
            ]

            msg = task_runner.launch(run_id, cmd, cwd=project_root)
            return msg, run_id, ""

        def poll_trt_status(run_id):
            if not run_id:
                return "", "", ""
            status = task_runner.status(run_id)
            log = task_runner.tail_log(run_id, 30)
            status_msg = f"Status: {status}"

            # Auto-fill TRT path on completion
            trt_path_update = gr.update()
            if status == "completed":
                run = store.get_run(run_id)
                if run:
                    try:
                        config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
                        engine_path = config.get("engine_path", "")
                        trt_path_update = gr.update(value=engine_path)
                        status_msg += f" — Engine built: {engine_path}"
                    except Exception:
                        pass

            return status_msg, log, trt_path_update

        # ── C1: Benchmark callbacks ──

        def launch_benchmark(model_path, trt_path, embodiment, num_iters, skip_compile, proj):
            if not model_path.strip():
                return "Model path is required", "", [], None
            pid = proj.get("id") if proj else None
            if not pid:
                return "Select a project first", "", [], None

            config = {
                "model_path": model_path,
                "embodiment_tag": embodiment,
                "num_iterations": int(num_iters),
                "trt_engine_path": trt_path if trt_path.strip() else None,
                "skip_compile": skip_compile,
            }
            run_id = store.create_run(
                project_id=pid,
                run_type="benchmark",
                config=config,
            )

            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            cmd = [
                venv_python,
                "scripts/deployment/benchmark_inference.py",
                "--model_path", model_path,
                "--embodiment_tag", embodiment,
                "--num_iterations", str(int(num_iters)),
            ]
            if trt_path.strip():
                cmd.extend(["--trt_engine_path", trt_path])
            if skip_compile:
                cmd.append("--skip_compile")

            msg = task_runner.launch(run_id, cmd, cwd=project_root)
            return msg, run_id, [], None

        def poll_benchmark_status(run_id, proj):
            if not run_id:
                return "", [], None
            status = task_runner.status(run_id)
            log = task_runner.tail_log(run_id, 100)
            status_msg = f"Status: {status}"

            # Parse results table from log
            results = _parse_benchmark_table(log)
            table_data = []
            chart = None

            if results:
                for r in results:
                    table_data.append([
                        r.get("Device", ""),
                        r.get("Mode", ""),
                        r.get("Data Processing", ""),
                        r.get("Backbone", ""),
                        r.get("Action Head", ""),
                        r.get("E2E", ""),
                        r.get("Frequency", ""),
                    ])

                # Build bar chart
                try:
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as plt

                    modes = [r.get("Mode", "") for r in results]
                    e2e_vals = []
                    for r in results:
                        try:
                            val = float(r.get("E2E", "0").replace("ms", "").strip())
                        except (ValueError, AttributeError):
                            val = 0
                        e2e_vals.append(val)

                    fig, ax = plt.subplots(figsize=(8, 4))
                    bars = ax.bar(range(len(modes)), e2e_vals, color=["#4c72b0", "#dd8452", "#55a868", "#c44e52"][:len(modes)])
                    ax.set_xticks(range(len(modes)))
                    ax.set_xticklabels(modes, rotation=15)
                    ax.set_ylabel("E2E Latency (ms)")
                    ax.set_title("Inference Timing Comparison")
                    ax.grid(True, alpha=0.3, axis="y")
                    plt.tight_layout()
                    chart = fig
                except Exception:
                    pass

                # Store parsed metrics in DB on completion (once)
                if status == "completed" and results:
                    # Check if we already saved results for this run
                    existing_evals = store.list_evaluations(run_id=run_id)
                    already_saved = any(
                        e.get("eval_type") == "benchmark" for e in existing_evals
                    )

                    if not already_saved:
                        # Update run metrics with first result summary
                        summary = {
                            "mode": results[0].get("Mode", ""),
                            "e2e_ms": results[0].get("E2E", ""),
                            "frequency_hz": results[0].get("Frequency", ""),
                        }
                        store.update_run(run_id, metrics=summary)

                        # Resolve model_id from run config
                        bench_model_id = None
                        pid_for_eval = proj.get("id") if proj else None
                        if pid_for_eval:
                            run_data = store.get_run(run_id)
                            if run_data:
                                try:
                                    run_config = json.loads(run_data["config"]) if isinstance(run_data["config"], str) else run_data["config"]
                                    bench_model_path = run_config.get("model_path", "")
                                    for m in store.list_models(project_id=pid_for_eval):
                                        if m["path"] == bench_model_path:
                                            bench_model_id = m["id"]
                                            break
                                except (json.JSONDecodeError, KeyError):
                                    pass

                            for r in results:
                                eval_metrics = {}
                                for k, v in r.items():
                                    eval_metrics[k.lower().replace(" ", "_")] = v
                                store.save_evaluation(
                                    run_id=run_id,
                                    model_id=bench_model_id or "",
                                    eval_type="benchmark",
                                    metrics=eval_metrics,
                                )

            return status_msg, table_data if table_data else [], chart

        # ── C2: Benchmark History callbacks ──

        def refresh_bench_history(proj):
            pid = proj.get("id") if proj else None
            table = _benchmark_history_table(store, pid)

            # Build comparison chart
            chart = None
            runs = store.list_runs(project_id=pid, run_type="benchmark")
            chart_data = []
            for r in runs:
                metrics = {}
                config = {}
                try:
                    if r.get("metrics"):
                        metrics = json.loads(r["metrics"]) if isinstance(r["metrics"], str) else r["metrics"]
                    config = json.loads(r["config"]) if isinstance(r["config"], str) else r["config"]
                except Exception:
                    pass
                freq = metrics.get("frequency_hz", "")
                model = config.get("model_path", "unknown")
                if len(model) > 20:
                    model = "..." + model[-17:]
                mode = metrics.get("mode", "")
                try:
                    freq_val = float(str(freq).replace("Hz", "").strip())
                    chart_data.append((f"{model}\n{mode}", freq_val))
                except (ValueError, TypeError):
                    pass

            if chart_data:
                try:
                    import matplotlib
                    matplotlib.use("Agg")
                    import matplotlib.pyplot as plt

                    labels, values = zip(*chart_data)
                    fig, ax = plt.subplots(figsize=(10, 4))
                    colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b2", "#937860"]
                    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]
                    ax.bar(range(len(labels)), values, color=bar_colors)
                    ax.set_xticks(range(len(labels)))
                    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
                    ax.set_ylabel("Frequency (Hz)")
                    ax.set_title("Benchmark Frequency Comparison")
                    ax.grid(True, alpha=0.3, axis="y")
                    plt.tight_layout()
                    chart = fig
                except Exception:
                    pass

            return table, chart

        # ── Wire up callbacks ──

        refresh_models_btn.click(
            refresh_models, inputs=[project_state], outputs=[model_table]
        )
        register_btn.click(
            register_model,
            inputs=[reg_name, reg_path, reg_embodiment, reg_step, reg_base_model, project_state],
            outputs=[reg_status],
        )
        deploy_btn.click(
            deploy_model,
            inputs=[deploy_model_path, deploy_embodiment, deploy_port],
            outputs=[deploy_status],
        )
        undeploy_btn.click(undeploy, outputs=[deploy_status])
        gen_cmd_btn.click(generate_command, inputs=[export_model_path], outputs=[export_cmd])

        # C1: ONNX Export
        onnx_export_btn.click(
            launch_onnx_export,
            inputs=[onnx_model_path, onnx_dataset_path, onnx_embodiment, onnx_output_dir, project_state],
            outputs=[onnx_status, onnx_run_id, trt_onnx_path],
        )
        onnx_timer = gr.Timer(5)
        onnx_timer.tick(
            poll_onnx_status,
            inputs=[onnx_run_id],
            outputs=[onnx_status, onnx_log, trt_onnx_path],
        )

        # C1: TensorRT Build
        trt_build_btn.click(
            launch_trt_build,
            inputs=[trt_onnx_path, trt_precision, project_state],
            outputs=[trt_status, trt_run_id, bench_trt_path],
        )
        trt_timer = gr.Timer(5)
        trt_timer.tick(
            poll_trt_status,
            inputs=[trt_run_id],
            outputs=[trt_status, trt_log, bench_trt_path],
        )

        # C1: Benchmark
        bench_run_btn.click(
            launch_benchmark,
            inputs=[bench_model_path, bench_trt_path, bench_embodiment, bench_num_iters, bench_skip_compile, project_state],
            outputs=[bench_status, bench_run_id, bench_results, bench_chart],
        )
        bench_timer = gr.Timer(5)
        bench_timer.tick(
            poll_benchmark_status,
            inputs=[bench_run_id, project_state],
            outputs=[bench_status, bench_results, bench_chart],
        )

        # C2: Benchmark History
        bench_history_refresh.click(
            refresh_bench_history,
            inputs=[project_state],
            outputs=[bench_history_table, bench_history_chart],
        )
