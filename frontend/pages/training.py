"""Training page — GR00T Finetune + Isaac Lab RL tabs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import gradio as gr

from frontend.components.progress_bar import render_progress_bar
from frontend.components.status_badge import render_status_badge
from frontend.constants import EMBODIMENT_CHOICES, TRAINING_PRESETS, ISAAC_LAB_ENVS, RL_ALGORITHMS
from frontend.services.task_runner import TaskRunner
from frontend.services.workspace import WorkspaceStore


def _run_history_table(store: WorkspaceStore, project_id: str | None) -> list[list]:
    runs = store.list_runs(project_id=project_id, run_type="training")
    rl_runs = store.list_runs(project_id=project_id, run_type="rl_training")
    all_runs = runs + rl_runs
    if not all_runs:
        return [["No training runs", "", "", "", "", ""]]
    rows = []
    for r in all_runs:
        config = {}
        try:
            config = json.loads(r["config"]) if isinstance(r["config"], str) else r["config"]
        except Exception:
            pass
        metrics = {}
        try:
            if r.get("metrics"):
                metrics = json.loads(r["metrics"]) if isinstance(r["metrics"], str) else r["metrics"]
        except Exception:
            pass
        loss = metrics.get("loss", "-")
        step = metrics.get("step", "-")
        dataset = config.get("dataset_path", config.get("environment", "-"))
        if len(str(dataset)) > 40:
            dataset = "..." + str(dataset)[-37:]
        rows.append([r["id"][:8], str(dataset), r["status"], str(loss), str(step), r.get("started_at", "")[:16] if r.get("started_at") else ""])
    return rows


def _dataset_choices(store: WorkspaceStore, project_id: str | None) -> list[str]:
    datasets = store.list_datasets(project_id=project_id)
    return [f"{ds['name']} | {ds['path']}" for ds in datasets]


def _model_choices(store: WorkspaceStore, project_id: str | None) -> list[str]:
    models = store.list_models(project_id=project_id)
    choices = ["nvidia/GR00T-N1.6-3B"]
    for m in models:
        choices.append(f"{m['name']} | {m['path']}")
    return choices


def create_training_page(
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
) -> dict:
    """Create the training page. Returns dict of components."""

    with gr.Column(visible=True) as page:
        gr.HTML('<div class="page-title">Training</div>')
        gr.HTML('<div style="color:var(--wybe-text-muted);font-size:13px;margin-top:-16px;margin-bottom:16px">Train policies (RL, IL, VLA)</div>')

        with gr.Tabs():
            # ── Tab 1: GR00T Finetune ──
            with gr.Tab("GR00T Finetune"):
                with gr.Row():
                    # ── Left: Configuration ──
                    with gr.Column(scale=1):
                        gr.HTML('<div class="section-title">Training Configuration</div>')

                        # Quick Start vs Custom toggle
                        config_mode = gr.Radio(
                            label="Mode",
                            choices=["Quick Start", "Custom"],
                            value="Quick Start",
                        )

                        # Preset dropdown
                        preset_dropdown = gr.Dropdown(
                            label="Preset",
                            choices=list(TRAINING_PRESETS.keys()),
                            value="Quick Start",
                        )

                        # Dataset selection
                        tr_dataset = gr.Dropdown(
                            label="Dataset",
                            choices=_dataset_choices(store, None),
                            allow_custom_value=True,
                        )
                        tr_base_model = gr.Dropdown(
                            label="Base Model",
                            choices=_model_choices(store, None),
                            value="nvidia/GR00T-N1.6-3B",
                            allow_custom_value=True,
                        )
                        tr_embodiment = gr.Dropdown(
                            label="Embodiment Tag",
                            choices=EMBODIMENT_CHOICES,
                            value="new_embodiment",
                        )

                        # Tuning flags
                        gr.Markdown("#### Tuning Flags")
                        with gr.Row():
                            tr_tune_llm = gr.Checkbox(label="LLM", value=False)
                            tr_tune_visual = gr.Checkbox(label="Visual", value=False)
                            tr_tune_projector = gr.Checkbox(label="Projector", value=True)
                            tr_tune_diffusion = gr.Checkbox(label="Diffusion", value=True)

                        # Hyperparameters with sliders
                        gr.Markdown("#### Hyperparameters")
                        with gr.Row():
                            tr_lr = gr.Number(label="Learning Rate", value=1e-4, step=1e-6)
                            tr_max_steps = gr.Slider(label="Max Steps", minimum=100, maximum=100000, value=10000, step=100)
                        with gr.Row():
                            tr_batch_size = gr.Slider(label="Batch Size", minimum=1, maximum=256, value=64, step=1)
                            tr_weight_decay = gr.Number(label="Weight Decay", value=1e-5, step=1e-6)
                        with gr.Row():
                            tr_warmup_ratio = gr.Slider(label="Warmup Ratio", minimum=0, maximum=0.5, value=0.05, step=0.01)
                            tr_save_steps = gr.Slider(label="Save Steps", minimum=100, maximum=10000, value=1000, step=100)

                        # Data
                        with gr.Row():
                            tr_shard_size = gr.Number(label="Shard Size", value=1024, precision=0)
                            tr_episode_rate = gr.Slider(label="Episode Rate", minimum=0.01, maximum=1.0, value=0.1, step=0.01)

                        # Output
                        tr_output_dir = gr.Textbox(label="Output Directory", value="./outputs")
                        tr_use_wandb = gr.Checkbox(label="Log to W&B", value=False)

                        # ── Advanced Config ──
                        with gr.Accordion("Advanced", open=False):
                            gr.Markdown("##### Distributed")
                            with gr.Row():
                                adv_deepspeed_stage = gr.Dropdown(label="DeepSpeed Stage", choices=["1", "2", "3"], value="2")
                                adv_num_gpus = gr.Number(label="Num GPUs", value=1, precision=0)
                                adv_gradient_checkpointing = gr.Checkbox(label="Gradient Ckpt", value=False)

                            gr.Markdown("##### Optimization")
                            with gr.Row():
                                adv_optimizer = gr.Dropdown(label="Optimizer", choices=["adamw_torch_fused", "adamw_torch", "adafactor", "paged_adamw_8bit"], value="adamw_torch_fused")
                                adv_lr_scheduler = gr.Dropdown(label="LR Scheduler", choices=["cosine", "linear", "polynomial"], value="cosine")
                            with gr.Row():
                                adv_max_grad_norm = gr.Number(label="Max Grad Norm", value=1.0)
                                adv_gradient_accum = gr.Number(label="Gradient Accum Steps", value=1, precision=0)

                            gr.Markdown("##### Precision")
                            with gr.Row():
                                adv_bf16 = gr.Checkbox(label="BF16", value=True)
                                adv_fp16 = gr.Checkbox(label="FP16", value=False)
                                adv_tf32 = gr.Checkbox(label="TF32", value=True)

                            gr.Markdown("##### Evaluation During Training")
                            with gr.Row():
                                adv_eval_enable = gr.Checkbox(label="Enable Eval", value=False)
                                adv_eval_steps = gr.Number(label="Eval Steps", value=500, precision=0)
                                adv_eval_split_ratio = gr.Number(label="Eval Split Ratio", value=0.1)

                            gr.Markdown("##### Image Augmentation")
                            with gr.Row():
                                adv_color_jitter = gr.Checkbox(label="Color Jitter", value=False)
                                adv_brightness = gr.Number(label="Brightness", value=0.3)
                                adv_contrast = gr.Number(label="Contrast", value=0.3)
                            with gr.Row():
                                adv_saturation = gr.Number(label="Saturation", value=0.3)
                                adv_hue = gr.Number(label="Hue", value=0.1)
                                adv_random_rotation = gr.Number(label="Rotation Angle", value=0, precision=0)

                            gr.Markdown("##### Saving & Other")
                            with gr.Row():
                                adv_save_total_limit = gr.Number(label="Save Total Limit", value=5, precision=0)
                                adv_state_dropout = gr.Number(label="State Dropout", value=0.0)
                            with gr.Row():
                                adv_dataloader_workers = gr.Number(label="Dataloader Workers", value=4, precision=0)
                                adv_enable_profiling = gr.Checkbox(label="Enable Profiler", value=False)

                        with gr.Row():
                            tr_launch_btn = gr.Button("Launch Training", variant="primary")
                            tr_stop_btn = gr.Button("Stop Training", variant="stop")
                        tr_status = gr.Textbox(label="Status", interactive=False)

                        gr.Markdown("---")

                        # Resume
                        gr.Markdown("#### Resume Training")
                        tr_resume_ckpt = gr.Textbox(label="Checkpoint Path", placeholder="/path/to/checkpoint-5000")
                        tr_resume_btn = gr.Button("Resume Training", variant="primary", size="sm")

                    # ── Right: Monitoring ──
                    with gr.Column(scale=1):
                        gr.HTML('<div class="section-title">Active Run Monitor</div>')
                        current_run_id = gr.State(value="")

                        # Progress bar
                        progress_html = gr.HTML(value="")

                        tr_log = gr.Code(label="Training Log", language=None, lines=18, interactive=False)
                        tr_loss_plot = gr.Plot(label="Loss Curve")
                        tr_checkpoints = gr.Dataframe(
                            headers=["Checkpoint", "Step"],
                            label="Saved Checkpoints",
                            interactive=False,
                        )

                        gr.Markdown("#### Register Checkpoint as Model")
                        with gr.Row():
                            ckpt_path = gr.Textbox(label="Checkpoint Path", placeholder="Paste from checkpoints above")
                            ckpt_name = gr.Textbox(label="Model Name", placeholder="my-model-v1")
                        reg_ckpt_btn = gr.Button("Register as Model", size="sm")
                        reg_ckpt_status = gr.Textbox(label="", interactive=False)

            # ── Tab 2: Isaac Lab RL ──
            with gr.Tab("Isaac Lab RL"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML('<div class="section-title">RL Configuration</div>')

                        rl_env = gr.Dropdown(
                            label="Environment",
                            choices=ISAAC_LAB_ENVS,
                            value=ISAAC_LAB_ENVS[0] if ISAAC_LAB_ENVS else None,
                        )
                        rl_algorithm = gr.Dropdown(
                            label="RL Algorithm",
                            choices=RL_ALGORITHMS,
                            value="PPO",
                        )
                        rl_num_envs = gr.Slider(label="Num Parallel Envs", minimum=1, maximum=4096, value=1024, step=1)
                        rl_total_timesteps = gr.Slider(label="Total Timesteps", minimum=10000, maximum=100000000, value=1000000, step=10000)
                        rl_domain_rand = gr.Checkbox(label="Domain Randomization", value=True)

                        gr.Markdown("---")

                        gr.HTML('<div class="section-title">Remote Execution</div>')
                        with gr.Row():
                            rl_remote_host = gr.Textbox(label="Remote Host", placeholder="runpod-host.example.com")
                            rl_remote_port = gr.Number(label="Port", value=22, precision=0)

                        with gr.Row():
                            rl_launch_btn = gr.Button("Launch RL Training", variant="primary")
                            rl_stop_btn = gr.Button("Stop", variant="stop")
                        rl_status = gr.Textbox(label="Status", interactive=False)

                    with gr.Column(scale=1):
                        gr.HTML('<div class="section-title">RL Monitor</div>')
                        rl_run_id = gr.State(value="")
                        rl_log = gr.Code(label="Training Log", language=None, lines=18, interactive=False)
                        rl_reward_plot = gr.Plot(label="Reward Curve")
                        rl_run_status = gr.HTML(value="")

        gr.Markdown("---")
        gr.HTML('<div class="section-title">Run History</div>')
        run_table = gr.Dataframe(
            headers=["Run ID", "Dataset", "Status", "Loss", "Step", "Started"],
            label="Training Runs",
            interactive=False,
            value=_run_history_table(store, None),
        )
        refresh_runs_btn = gr.Button("Refresh", size="sm")

    # ── Callbacks ──

    def apply_preset(preset_name):
        preset = TRAINING_PRESETS.get(preset_name, TRAINING_PRESETS["Quick Start"])
        return (
            preset["learning_rate"],
            preset["max_steps"],
            preset["global_batch_size"],
            preset["weight_decay"],
            preset["warmup_ratio"],
            preset["save_steps"],
            preset["shard_size"],
            preset["episode_sampling_rate"],
        )

    def _build_training_cmd(
        dataset, base_model, embodiment, tune_llm, tune_visual,
        tune_projector, tune_diffusion, lr, max_steps, batch_size,
        weight_decay, warmup_ratio, save_steps, shard_size,
        episode_rate, output_dir, use_wandb,
        deepspeed_stage, num_gpus, gradient_checkpointing,
        optimizer, lr_scheduler, max_grad_norm, gradient_accum,
        bf16, fp16, tf32, eval_enable, eval_steps, eval_split_ratio,
        color_jitter, brightness, contrast, saturation, hue,
        random_rotation, save_total_limit, state_dropout,
        dataloader_workers, enable_profiling,
        resume_ckpt_path=None,
    ):
        # Extract path from dropdown selection
        if "|" in dataset:
            dataset = dataset.split("|")[-1].strip()
        if "|" in base_model:
            base_model = base_model.split("|")[-1].strip()

        config = {
            "base_model": base_model, "dataset_path": dataset,
            "embodiment_tag": embodiment,
            "tune_llm": tune_llm, "tune_visual": tune_visual,
            "tune_projector": tune_projector, "tune_diffusion": tune_diffusion,
            "learning_rate": lr, "max_steps": int(max_steps),
            "global_batch_size": int(batch_size), "weight_decay": weight_decay,
            "warmup_ratio": warmup_ratio, "save_steps": int(save_steps),
            "shard_size": int(shard_size), "episode_sampling_rate": episode_rate,
            "output_dir": output_dir, "use_wandb": use_wandb,
            "deepspeed_stage": int(deepspeed_stage), "num_gpus": int(num_gpus),
        }
        if resume_ckpt_path:
            config["resume_checkpoint_path"] = resume_ckpt_path

        venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
        cmd = [
            venv_python, "-m", "gr00t.experiment.launch_finetune",
            "--base_model_path", base_model, "--dataset_path", dataset,
            "--embodiment_tag", embodiment,
            "--learning_rate", str(lr), "--max_steps", str(int(max_steps)),
            "--global_batch_size", str(int(batch_size)),
            "--weight_decay", str(weight_decay), "--warmup_ratio", str(warmup_ratio),
            "--save_steps", str(int(save_steps)), "--shard_size", str(int(shard_size)),
            "--episode_sampling_rate", str(episode_rate), "--output_dir", output_dir,
        ]

        if tune_llm: cmd.append("--tune_llm")
        if tune_visual: cmd.append("--tune_visual")
        if not tune_projector: cmd.append("--no-tune_projector")
        if not tune_diffusion: cmd.append("--no-tune_diffusion_model")
        if use_wandb: cmd.append("--use_wandb")

        cmd.extend(["--num_gpus", str(int(num_gpus))])
        cmd.extend(["--gradient_accumulation_steps", str(int(gradient_accum))])
        cmd.extend(["--save_total_limit", str(int(save_total_limit))])
        cmd.extend(["--dataloader_num_workers", str(int(dataloader_workers))])

        if int(deepspeed_stage) != 2: cmd.extend(["--deepspeed_stage", str(int(deepspeed_stage))])
        if gradient_checkpointing: cmd.append("--gradient_checkpointing")
        if optimizer != "adamw_torch_fused": cmd.extend(["--optim", optimizer])
        if lr_scheduler != "cosine": cmd.extend(["--lr_scheduler_type", lr_scheduler])
        if color_jitter:
            cmd.extend(["--color_jitter_params", "brightness", str(brightness), "contrast", str(contrast), "saturation", str(saturation), "hue", str(hue)])
        if int(random_rotation) > 0: cmd.extend(["--random_rotation_angle", str(int(random_rotation))])
        if state_dropout > 0: cmd.extend(["--state_dropout_prob", str(state_dropout)])
        if enable_profiling: cmd.append("--enable_profiling")
        if eval_enable:
            cmd.extend(["--eval_strategy", "steps", "--eval_steps", str(int(eval_steps))])

        if resume_ckpt_path:
            ckpt_parent = str(Path(resume_ckpt_path).parent)
            for i, arg in enumerate(cmd):
                if arg == "--output_dir" and i + 1 < len(cmd):
                    cmd[i + 1] = ckpt_parent
                    break
            config["output_dir"] = ckpt_parent

        return config, cmd

    def launch_training(
        dataset, base_model, embodiment, tune_llm, tune_visual,
        tune_projector, tune_diffusion, lr, max_steps, batch_size,
        weight_decay, warmup_ratio, save_steps, shard_size,
        episode_rate, output_dir, use_wandb,
        deepspeed_stage, num_gpus, gradient_checkpointing,
        optimizer, lr_scheduler, max_grad_norm, gradient_accum,
        bf16, fp16, tf32, eval_enable, eval_steps, eval_split_ratio,
        color_jitter, brightness, contrast, saturation, hue,
        random_rotation, save_total_limit, state_dropout,
        dataloader_workers, enable_profiling, proj,
    ):
        if not dataset or not dataset.strip():
            return "Error: dataset is required", ""
        pid = proj.get("id") if proj else None
        if not pid:
            return "Error: select a project first", ""

        config, cmd = _build_training_cmd(
            dataset, base_model, embodiment, tune_llm, tune_visual,
            tune_projector, tune_diffusion, lr, max_steps, batch_size,
            weight_decay, warmup_ratio, save_steps, shard_size,
            episode_rate, output_dir, use_wandb,
            deepspeed_stage, num_gpus, gradient_checkpointing,
            optimizer, lr_scheduler, max_grad_norm, gradient_accum,
            bf16, fp16, tf32, eval_enable, eval_steps, eval_split_ratio,
            color_jitter, brightness, contrast, saturation, hue,
            random_rotation, save_total_limit, state_dropout,
            dataloader_workers, enable_profiling,
        )

        run_id = store.create_run(project_id=pid, run_type="training", config=config)
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id

    def resume_training(
        resume_ckpt_path,
        dataset, base_model, embodiment, tune_llm, tune_visual,
        tune_projector, tune_diffusion, lr, max_steps, batch_size,
        weight_decay, warmup_ratio, save_steps, shard_size,
        episode_rate, output_dir, use_wandb,
        deepspeed_stage, num_gpus, gradient_checkpointing,
        optimizer, lr_scheduler, max_grad_norm, gradient_accum,
        bf16, fp16, tf32, eval_enable, eval_steps, eval_split_ratio,
        color_jitter, brightness, contrast, saturation, hue,
        random_rotation, save_total_limit, state_dropout,
        dataloader_workers, enable_profiling, proj,
    ):
        if not resume_ckpt_path.strip():
            return "Error: checkpoint path is required", ""
        if not dataset or not dataset.strip():
            return "Error: dataset is required", ""
        pid = proj.get("id") if proj else None
        if not pid:
            return "Error: select a project first", ""

        config, cmd = _build_training_cmd(
            dataset, base_model, embodiment, tune_llm, tune_visual,
            tune_projector, tune_diffusion, lr, max_steps, batch_size,
            weight_decay, warmup_ratio, save_steps, shard_size,
            episode_rate, output_dir, use_wandb,
            deepspeed_stage, num_gpus, gradient_checkpointing,
            optimizer, lr_scheduler, max_grad_norm, gradient_accum,
            bf16, fp16, tf32, eval_enable, eval_steps, eval_split_ratio,
            color_jitter, brightness, contrast, saturation, hue,
            random_rotation, save_total_limit, state_dropout,
            dataloader_workers, enable_profiling,
            resume_ckpt_path=resume_ckpt_path,
        )

        run_id = store.create_run(project_id=pid, run_type="training", config=config)
        msg = task_runner.launch(run_id, cmd, cwd=project_root)
        return msg, run_id

    def stop_training(run_id):
        return task_runner.stop(run_id) if run_id else "No active training run"

    def refresh_log(run_id):
        return task_runner.tail_log(run_id, 50) if run_id else ""

    def refresh_loss_plot(run_id):
        if not run_id:
            return None
        log_text = task_runner.tail_log(run_id, 500)
        steps, losses = [], []
        for line in log_text.splitlines():
            m = re.search(r"'loss':\s*([\d.e+-]+).*'step':\s*(\d+)", line)
            if m:
                losses.append(float(m.group(1)))
                steps.append(int(m.group(2)))
        if not steps:
            return None
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=steps, y=losses, mode="lines", name="Loss", line=dict(color="#3b82f6")))
            fig.update_layout(
                title="Training Loss", xaxis_title="Step", yaxis_title="Loss",
                template="plotly_dark", height=350,
                margin=dict(l=40, r=20, t=40, b=40),
            )
            return fig
        except Exception:
            return None

    def refresh_progress(run_id):
        if not run_id:
            return ""
        log_text = task_runner.tail_log(run_id, 500)
        max_steps = 10000
        current_step = 0
        for line in log_text.splitlines():
            m = re.search(r"'step':\s*(\d+)", line)
            if m:
                current_step = int(m.group(1))
        # Try to get max_steps from run config
        run = store.get_run(run_id)
        if run:
            try:
                config = json.loads(run["config"]) if isinstance(run["config"], str) else run["config"]
                max_steps = config.get("max_steps", 10000)
            except Exception:
                pass
        pct = (current_step / max_steps * 100) if max_steps > 0 else 0
        status = task_runner.status(run_id)
        return render_progress_bar(pct, status, f"{current_step:,} / {max_steps:,} steps")

    def refresh_checkpoints(run_id):
        if not run_id:
            return []
        log_text = task_runner.tail_log(run_id, 500)
        rows = []
        for line in log_text.splitlines():
            m = re.search(r"Saving model checkpoint to (.+?)(?:\s|$)", line)
            if m:
                ckpt = m.group(1).strip()
                step_m = re.search(r"checkpoint-(\d+)", ckpt)
                rows.append([ckpt, step_m.group(1) if step_m else "?"])
        return rows if rows else []

    def refresh_runs(proj):
        pid = proj.get("id") if proj else None
        return _run_history_table(store, pid)

    def register_checkpoint(path, name, proj):
        if not path.strip() or not name.strip():
            return "Checkpoint path and model name are required"
        pid = proj.get("id") if proj else None
        if not pid:
            return "Select a project first"
        step_m = re.search(r"checkpoint-(\d+)", path)
        step = int(step_m.group(1)) if step_m else None
        project = store.get_project(pid)
        mid = store.register_model(
            project_id=pid, name=name, path=path,
            embodiment_tag=project["embodiment_tag"] if project else "new_embodiment",
            step=step,
            base_model=project["base_model"] if project else "nvidia/GR00T-N1.6-3B",
        )
        return f"Model registered: {mid}"

    # Isaac Lab RL callbacks
    def launch_rl_training(env, algorithm, num_envs, total_timesteps, domain_rand, remote_host, remote_port, proj):
        pid = proj.get("id") if proj else None
        if not pid:
            return "Error: select a project first", ""
        config = {
            "environment": env,
            "algorithm": algorithm,
            "num_envs": int(num_envs),
            "total_timesteps": int(total_timesteps),
            "domain_randomization": domain_rand,
            "remote_host": remote_host,
            "remote_port": int(remote_port),
        }
        run_id = store.create_run(project_id=pid, run_type="rl_training", config=config)
        return f"Isaac Lab RL training queued: {env} with {algorithm} ({int(num_envs)} envs, {int(total_timesteps)} timesteps). Run ID: {run_id}", run_id

    def stop_rl_training(run_id):
        return task_runner.stop(run_id) if run_id else "No active RL training run"

    def refresh_rl_log(run_id):
        return task_runner.tail_log(run_id, 50) if run_id else ""

    def refresh_rl_reward_plot(run_id):
        if not run_id:
            return None
        log_text = task_runner.tail_log(run_id, 500)
        steps, rewards = [], []
        for line in log_text.splitlines():
            m = re.search(r"timestep[s]?:\s*(\d+).*reward:\s*([\d.e+-]+)", line, re.IGNORECASE)
            if m:
                steps.append(int(m.group(1)))
                rewards.append(float(m.group(2)))
        if not steps:
            return None
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=steps, y=rewards, mode="lines", name="Reward", line=dict(color="#22c55e")))
            fig.update_layout(
                title="Episode Reward", xaxis_title="Timestep", yaxis_title="Reward",
                template="plotly_dark", height=350,
                margin=dict(l=40, r=20, t=40, b=40),
            )
            return fig
        except Exception:
            return None

    def refresh_rl_status(run_id):
        if not run_id:
            return ""
        status = task_runner.status(run_id)
        return render_status_badge(status)

    # All shared inputs for GR00T finetune
    _shared_inputs = [
        tr_dataset, tr_base_model, tr_embodiment,
        tr_tune_llm, tr_tune_visual, tr_tune_projector, tr_tune_diffusion,
        tr_lr, tr_max_steps, tr_batch_size, tr_weight_decay,
        tr_warmup_ratio, tr_save_steps, tr_shard_size,
        tr_episode_rate, tr_output_dir, tr_use_wandb,
        adv_deepspeed_stage, adv_num_gpus, adv_gradient_checkpointing,
        adv_optimizer, adv_lr_scheduler, adv_max_grad_norm, adv_gradient_accum,
        adv_bf16, adv_fp16, adv_tf32,
        adv_eval_enable, adv_eval_steps, adv_eval_split_ratio,
        adv_color_jitter, adv_brightness, adv_contrast, adv_saturation, adv_hue,
        adv_random_rotation, adv_save_total_limit, adv_state_dropout,
        adv_dataloader_workers, adv_enable_profiling,
    ]

    # Wire callbacks
    preset_dropdown.change(
        apply_preset, inputs=[preset_dropdown],
        outputs=[tr_lr, tr_max_steps, tr_batch_size, tr_weight_decay, tr_warmup_ratio, tr_save_steps, tr_shard_size, tr_episode_rate],
    )
    tr_launch_btn.click(launch_training, inputs=_shared_inputs + [project_state], outputs=[tr_status, current_run_id])
    tr_resume_btn.click(resume_training, inputs=[tr_resume_ckpt] + _shared_inputs + [project_state], outputs=[tr_status, current_run_id])
    tr_stop_btn.click(stop_training, inputs=[current_run_id], outputs=[tr_status])
    reg_ckpt_btn.click(register_checkpoint, inputs=[ckpt_path, ckpt_name, project_state], outputs=[reg_ckpt_status])
    refresh_runs_btn.click(refresh_runs, inputs=[project_state], outputs=[run_table])

    # Isaac Lab RL callbacks
    rl_launch_btn.click(launch_rl_training, inputs=[rl_env, rl_algorithm, rl_num_envs, rl_total_timesteps, rl_domain_rand, rl_remote_host, rl_remote_port, project_state], outputs=[rl_status, rl_run_id])
    rl_stop_btn.click(stop_rl_training, inputs=[rl_run_id], outputs=[rl_status])

    return {
        "page": page,
        "current_run_id": current_run_id,
        "refresh_log": refresh_log,
        "refresh_loss_plot": refresh_loss_plot,
        "refresh_progress": refresh_progress,
        "refresh_checkpoints": refresh_checkpoints,
        "tr_log": tr_log,
        "tr_loss_plot": tr_loss_plot,
        "tr_checkpoints": tr_checkpoints,
        "progress_html": progress_html,
        # RL-specific
        "rl_run_id": rl_run_id,
        "refresh_rl_log": refresh_rl_log,
        "refresh_rl_reward_plot": refresh_rl_reward_plot,
        "refresh_rl_status": refresh_rl_status,
        "rl_log": rl_log,
        "rl_reward_plot": rl_reward_plot,
        "rl_run_status": rl_run_status,
    }
