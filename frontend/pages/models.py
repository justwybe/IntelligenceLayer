"""Models page — model registry, deploy to fleet, optimize, benchmark."""

from __future__ import annotations

import json
from pathlib import Path

import gradio as gr

from frontend.constants import EMBODIMENT_CHOICES
from frontend.services.server_manager import ServerManager
from frontend.services.task_runner import TaskRunner
from frontend.services.workspace import WorkspaceStore


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
        rows.append([m["name"], m["path"], str(m.get("step", "")), m.get("embodiment_tag", ""), eval_summary or "-"])
    return rows


def _model_dropdown_choices(store: WorkspaceStore, project_id: str | None) -> list[str]:
    models = store.list_models(project_id=project_id)
    return [f"{m['name']} | {m['path']}" for m in models]


def _parse_benchmark_table(log_text: str) -> list[dict]:
    results = []
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
            row = {}
            for j, h in enumerate(headers):
                row[h] = cells[j] if j < len(cells) else ""
            results.append(row)
    return results


def _benchmark_history_table(store: WorkspaceStore, project_id: str | None) -> list[list]:
    runs = store.list_runs(project_id=project_id, run_type="benchmark")
    if not runs:
        return [["No benchmark runs", "", "", "", ""]]
    rows = []
    for r in runs:
        metrics, config = {}, {}
        try:
            if r.get("metrics"):
                metrics = json.loads(r["metrics"]) if isinstance(r["metrics"], str) else r["metrics"]
            config = json.loads(r["config"]) if isinstance(r["config"], str) else r["config"]
        except Exception:
            pass
        model = config.get("model_path", "-")
        if len(model) > 30:
            model = "..." + model[-27:]
        rows.append([model, metrics.get("mode", "-"), str(metrics.get("e2e_ms", "-")), str(metrics.get("frequency_hz", "-")), r.get("started_at", "")[:16] if r.get("started_at") else ""])
    return rows


def create_models_page(
    server_manager: ServerManager,
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
) -> dict:
    """Create the models page. Returns dict of components."""

    with gr.Column(visible=True) as page:
        gr.HTML('<div class="page-title">Models</div>')
        gr.HTML('<div style="color:var(--wybe-text-muted);font-size:13px;margin-top:-16px;margin-bottom:16px">Version & deploy</div>')

        # ── Model Registry (top, prominent) ──
        gr.HTML('<div class="section-title">Model Registry</div>')
        model_table = gr.Dataframe(
            headers=["Name", "Path", "Step", "Embodiment", "Eval Scores"],
            label="Registered Models", interactive=False,
            value=_models_table(store, None),
        )
        refresh_models_btn = gr.Button("Refresh", size="sm")

        # ── Register Model ──
        with gr.Accordion("Register Model Manually", open=False):
            with gr.Row():
                reg_name = gr.Textbox(label="Name", placeholder="my-finetuned-v1")
                reg_path = gr.Textbox(label="Checkpoint Path", placeholder="/path/to/checkpoint-5000")
            with gr.Row():
                reg_embodiment = gr.Dropdown(label="Embodiment Tag", choices=EMBODIMENT_CHOICES, value="new_embodiment")
                reg_step = gr.Number(label="Step", value=0, precision=0)
                reg_base_model = gr.Textbox(label="Base Model", value="nvidia/GR00T-N1.6-3B")
            register_btn = gr.Button("Register Model", variant="primary", size="sm")
            reg_status = gr.Textbox(label="Status", interactive=False)

        gr.Markdown("---")

        with gr.Tabs():
            # ── Tab 1: Deploy to Fleet ──
            with gr.Tab("Deploy to Fleet"):
                gr.HTML('<div class="section-title">Deploy to Server</div>')
                with gr.Row():
                    deploy_model = gr.Dropdown(
                        label="Model",
                        choices=_model_dropdown_choices(store, None),
                        allow_custom_value=True,
                    )
                    deploy_embodiment = gr.Dropdown(label="Embodiment", choices=EMBODIMENT_CHOICES, value="new_embodiment")
                    deploy_port = gr.Number(label="Port", value=5555, precision=0)
                with gr.Row():
                    deploy_btn = gr.Button("Deploy", variant="primary")
                    undeploy_btn = gr.Button("Stop Server", variant="stop")
                deploy_status = gr.Textbox(label="Deploy Status", interactive=False)

                gr.Markdown("---")

                # Export Command
                with gr.Accordion("Export / Launch Command", open=False):
                    export_model_path = gr.Textbox(label="Model Path", placeholder="Path to model checkpoint")
                    export_cmd = gr.Code(label="Server Launch Command", language="shell", interactive=False, lines=3)
                    gen_cmd_btn = gr.Button("Generate Command", size="sm")

            # ── Tab 2: Optimize ──
            with gr.Tab("Optimize"):
                # ONNX Export
                gr.HTML('<div class="section-title">Export to ONNX</div>')
                with gr.Row():
                    onnx_model_path = gr.Textbox(label="Model Path", placeholder="/path/to/model")
                    onnx_dataset_path = gr.Textbox(label="Dataset Path", placeholder="/path/to/dataset")
                with gr.Row():
                    onnx_embodiment = gr.Dropdown(label="Embodiment Tag", choices=EMBODIMENT_CHOICES, value="new_embodiment")
                    onnx_output_dir = gr.Textbox(label="Output Dir", placeholder="/path/to/onnx_output")
                onnx_export_btn = gr.Button("Export ONNX", variant="primary", size="sm")
                onnx_status = gr.Textbox(label="Status", interactive=False)
                onnx_log = gr.Code(label="Log Output", language=None, lines=8, interactive=False)
                onnx_run_id = gr.State(value="")

                gr.Markdown("---")

                # TensorRT Build
                gr.HTML('<div class="section-title">Build TensorRT Engine</div>')
                with gr.Row():
                    trt_onnx_path = gr.Textbox(label="ONNX Path", placeholder="Auto-filled from ONNX export")
                    trt_precision = gr.Dropdown(label="Precision", choices=["bf16", "fp16", "fp32"], value="bf16")
                trt_build_btn = gr.Button("Build Engine", variant="primary", size="sm")
                trt_status = gr.Textbox(label="Status", interactive=False)
                trt_log = gr.Code(label="Log Output", language=None, lines=8, interactive=False)
                trt_run_id = gr.State(value="")

            # ── Tab 3: Benchmark ──
            with gr.Tab("Benchmark"):
                gr.HTML('<div class="section-title">Benchmark Inference</div>')
                with gr.Row():
                    bench_model_path = gr.Textbox(label="Model Path", placeholder="/path/to/model")
                    bench_trt_path = gr.Textbox(label="TensorRT Engine Path (optional)")
                with gr.Row():
                    bench_embodiment = gr.Dropdown(label="Embodiment Tag", choices=EMBODIMENT_CHOICES, value="new_embodiment")
                    bench_num_iters = gr.Slider(label="Num Iterations", minimum=10, maximum=1000, value=100, step=10)
                    bench_skip_compile = gr.Checkbox(label="Skip Compile", value=False)
                bench_run_btn = gr.Button("Run Benchmark", variant="primary", size="sm")
                bench_status = gr.Textbox(label="Status", interactive=False)
                bench_results = gr.Dataframe(
                    headers=["Device", "Mode", "Data Processing", "Backbone", "Action Head", "E2E", "Frequency"],
                    label="Benchmark Results", interactive=False,
                )
                bench_chart = gr.Plot(label="Timing Comparison")
                bench_run_id = gr.State(value="")

                gr.Markdown("---")

                # Benchmark History
                gr.HTML('<div class="section-title">Benchmark History</div>')
                bench_history_refresh = gr.Button("Refresh", size="sm")
                bench_history_table = gr.Dataframe(
                    headers=["Model", "Mode", "E2E (ms)", "Freq (Hz)", "Date"],
                    label="Benchmark History", interactive=False,
                    value=_benchmark_history_table(store, None),
                )
                bench_history_chart = gr.Plot(label="Frequency Comparison")

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
        mid = store.register_model(project_id=pid, name=name, path=path, base_model=base_model, embodiment_tag=embodiment, step=int(step))
        return f"Model registered: {mid}"

    def deploy_model_fn(model_choice, embodiment, port):
        model_path = model_choice.split("|")[-1].strip() if "|" in model_choice else model_choice
        if not model_path.strip():
            return "Model path is required"
        return server_manager.start(model_path, embodiment, port=int(port))

    def undeploy():
        return server_manager.stop()

    def generate_command(model_path):
        if not model_path.strip():
            return ""
        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        return f"{venv_python} -m gr00t.eval.run_gr00t_server --model_path {model_path} --embodiment_tag new_embodiment --port 5555 --device cuda --host 0.0.0.0"

    def launch_onnx_export(model_path, dataset_path, embodiment, output_dir, proj):
        if not model_path.strip() or not dataset_path.strip() or not output_dir.strip():
            return "All fields are required", "", ""
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first", "", ""
        config = {"model_path": model_path, "dataset_path": dataset_path, "embodiment_tag": embodiment, "output_dir": output_dir}
        run_id = store.create_run(project_id=pid, run_type="onnx_export", config=config)
        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        cmd = [venv_python, "scripts/deployment/export_onnx_n1d6.py", "--model_path", model_path, "--dataset_path", dataset_path, "--embodiment_tag", embodiment, "--output_dir", output_dir]
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id, ""

    def poll_onnx(run_id):
        if not run_id:
            return "", "", gr.update()
        status = task_runner.status(run_id)
        log = task_runner.tail_log(run_id, 30)
        status_msg = f"Status: {status}"
        onnx_path_update = gr.update()
        if status == "completed":
            run = store.get_run(run_id)
            if run:
                try:
                    config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
                    expected_onnx = str(Path(config.get("output_dir", "")) / "dit_model.onnx")
                    onnx_path_update = gr.update(value=expected_onnx)
                    status_msg += f" — ONNX exported to {expected_onnx}"
                except Exception:
                    pass
        return status_msg, log, onnx_path_update

    def launch_trt(onnx_path, precision, proj):
        if not onnx_path.strip():
            return "ONNX path is required", "", ""
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first", "", ""
        engine_path = onnx_path.replace(".onnx", f".{precision}.trt")
        config = {"onnx_path": onnx_path, "engine_path": engine_path, "precision": precision}
        run_id = store.create_run(project_id=pid, run_type="tensorrt_build", config=config)
        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        cmd = [venv_python, "scripts/deployment/build_tensorrt_engine.py", "--onnx", onnx_path, "--engine", engine_path, "--precision", precision]
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id, ""

    def poll_trt(run_id):
        if not run_id:
            return "", "", gr.update()
        status = task_runner.status(run_id)
        log = task_runner.tail_log(run_id, 30)
        status_msg = f"Status: {status}"
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

    def launch_benchmark(model_path, trt_path, embodiment, num_iters, skip_compile, proj):
        if not model_path.strip():
            return "Model path is required", "", [], None
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first", "", [], None
        config = {"model_path": model_path, "embodiment_tag": embodiment, "num_iterations": int(num_iters), "trt_engine_path": trt_path if trt_path.strip() else None, "skip_compile": skip_compile}
        run_id = store.create_run(project_id=pid, run_type="benchmark", config=config)
        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        cmd = [venv_python, "scripts/deployment/benchmark_inference.py", "--model_path", model_path, "--embodiment_tag", embodiment, "--num_iterations", str(int(num_iters))]
        if trt_path.strip():
            cmd.extend(["--trt_engine_path", trt_path])
        if skip_compile:
            cmd.append("--skip_compile")
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id, [], None

    def poll_benchmark(run_id, proj):
        if not run_id:
            return "", [], None
        status = task_runner.status(run_id)
        log = task_runner.tail_log(run_id, 100)
        status_msg = f"Status: {status}"
        results = _parse_benchmark_table(log)
        table_data = []
        chart = None
        if results:
            for r in results:
                table_data.append([r.get("Device", ""), r.get("Mode", ""), r.get("Data Processing", ""), r.get("Backbone", ""), r.get("Action Head", ""), r.get("E2E", ""), r.get("Frequency", "")])
            try:
                import plotly.graph_objects as go
                modes = [r.get("Mode", "") for r in results]
                e2e_vals = []
                for r in results:
                    try:
                        e2e_vals.append(float(r.get("E2E", "0").replace("ms", "").strip()))
                    except (ValueError, AttributeError):
                        e2e_vals.append(0)
                chart = go.Figure()
                chart.add_trace(go.Bar(x=modes, y=e2e_vals, marker_color=["#3b82f6", "#eab308", "#22c55e", "#ef4444"][:len(modes)]))
                chart.update_layout(title="Inference Timing", yaxis_title="E2E Latency (ms)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40))
            except Exception:
                pass

            if status == "completed" and results:
                existing_evals = store.list_evaluations(run_id=run_id)
                if not any(e.get("eval_type") == "benchmark" for e in existing_evals):
                    summary = {"mode": results[0].get("Mode", ""), "e2e_ms": results[0].get("E2E", ""), "frequency_hz": results[0].get("Frequency", "")}
                    store.update_run(run_id, metrics=summary)
                    pid = proj.get("id") if proj else None
                    if pid:
                        for r in results:
                            eval_metrics = {k.lower().replace(" ", "_"): v for k, v in r.items()}
                            store.save_evaluation(run_id=run_id, model_id="", eval_type="benchmark", metrics=eval_metrics)

        return status_msg, table_data if table_data else [], chart

    def refresh_bench_history(proj):
        pid = proj.get("id") if proj else None
        table = _benchmark_history_table(store, pid)
        chart = None
        runs = store.list_runs(project_id=pid, run_type="benchmark")
        chart_data = []
        for r in runs:
            metrics, config = {}, {}
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
            try:
                freq_val = float(str(freq).replace("Hz", "").strip())
                chart_data.append((f"{model}", freq_val))
            except (ValueError, TypeError):
                pass
        if chart_data:
            try:
                import plotly.graph_objects as go
                labels, values = zip(*chart_data)
                chart = go.Figure()
                chart.add_trace(go.Bar(x=list(labels), y=list(values), marker_color="#3b82f6"))
                chart.update_layout(title="Benchmark Frequency Comparison", yaxis_title="Frequency (Hz)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40))
            except Exception:
                pass
        return table, chart

    # Wire callbacks
    refresh_models_btn.click(refresh_models, inputs=[project_state], outputs=[model_table])
    register_btn.click(register_model, inputs=[reg_name, reg_path, reg_embodiment, reg_step, reg_base_model, project_state], outputs=[reg_status])
    deploy_btn.click(deploy_model_fn, inputs=[deploy_model, deploy_embodiment, deploy_port], outputs=[deploy_status])
    undeploy_btn.click(undeploy, outputs=[deploy_status])
    gen_cmd_btn.click(generate_command, inputs=[export_model_path], outputs=[export_cmd])
    onnx_export_btn.click(launch_onnx_export, inputs=[onnx_model_path, onnx_dataset_path, onnx_embodiment, onnx_output_dir, project_state], outputs=[onnx_status, onnx_run_id, trt_onnx_path])
    trt_build_btn.click(launch_trt, inputs=[trt_onnx_path, trt_precision, project_state], outputs=[trt_status, trt_run_id, bench_trt_path])
    bench_run_btn.click(launch_benchmark, inputs=[bench_model_path, bench_trt_path, bench_embodiment, bench_num_iters, bench_skip_compile, project_state], outputs=[bench_status, bench_run_id, bench_results, bench_chart])
    bench_history_refresh.click(refresh_bench_history, inputs=[project_state], outputs=[bench_history_table, bench_history_chart])

    return {
        "page": page,
        "onnx_run_id": onnx_run_id,
        "trt_run_id": trt_run_id,
        "bench_run_id": bench_run_id,
        "poll_onnx": poll_onnx,
        "poll_trt": poll_trt,
        "poll_benchmark": poll_benchmark,
        "onnx_status": onnx_status,
        "onnx_log": onnx_log,
        "trt_onnx_path": trt_onnx_path,
        "trt_status": trt_status,
        "trt_log": trt_log,
        "bench_trt_path": bench_trt_path,
        "bench_status": bench_status,
        "bench_results": bench_results,
        "bench_chart": bench_chart,
        "project_state": project_state,
    }
