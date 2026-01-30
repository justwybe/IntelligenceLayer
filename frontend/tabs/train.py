from __future__ import annotations

"""Train tab — launch fine-tuning jobs with DB tracking, run history, loss curves,
resume from checkpoint, and advanced training configuration."""

import json
import re
from pathlib import Path

import gradio as gr

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


def _run_history_table(
    store: WorkspaceStore, project_id: str | None
) -> list[list]:
    runs = store.list_runs(project_id=project_id, run_type="training")
    if not runs:
        return [["No training runs", "", "", "", "", ""]]
    rows = []
    for r in runs:
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
        dataset = config.get("dataset_path", "-")
        if len(dataset) > 40:
            dataset = "..." + dataset[-37:]
        rows.append([
            r["id"][:8],
            dataset,
            r["status"],
            str(loss),
            str(step),
            r.get("started_at", "")[:16] if r.get("started_at") else "",
        ])
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


def create_train_tab(
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
):
    with gr.Tab("Train"):
        gr.Markdown("## Train")

        with gr.Row():
            # ── Left: New run form ──
            with gr.Column(scale=1):
                gr.Markdown("### New Training Run")

                tr_dataset = gr.Textbox(
                    label="Dataset Path",
                    placeholder="/path/to/training/data",
                )
                tr_base_model = gr.Textbox(
                    label="Base Model Path",
                    value="nvidia/GR00T-N1.6-3B",
                )
                tr_embodiment = gr.Dropdown(
                    label="Embodiment Tag",
                    choices=EMBODIMENT_CHOICES,
                    value="new_embodiment",
                )

                gr.Markdown("#### Tuning Flags")
                with gr.Row():
                    tr_tune_llm = gr.Checkbox(label="LLM", value=False)
                    tr_tune_visual = gr.Checkbox(label="Visual", value=False)
                    tr_tune_projector = gr.Checkbox(label="Projector", value=True)
                    tr_tune_diffusion = gr.Checkbox(label="Diffusion", value=True)

                gr.Markdown("#### Hyperparameters")
                with gr.Row():
                    tr_lr = gr.Number(label="Learning Rate", value=1e-4, step=1e-6)
                    tr_max_steps = gr.Number(label="Max Steps", value=10000, precision=0)
                with gr.Row():
                    tr_batch_size = gr.Number(label="Batch Size", value=64, precision=0)
                    tr_weight_decay = gr.Number(label="Weight Decay", value=1e-5, step=1e-6)
                with gr.Row():
                    tr_warmup_ratio = gr.Number(label="Warmup Ratio", value=0.05)
                    tr_save_steps = gr.Number(label="Save Steps", value=1000, precision=0)

                gr.Markdown("#### Data")
                with gr.Row():
                    tr_shard_size = gr.Number(label="Shard Size", value=1024, precision=0)
                    tr_episode_rate = gr.Number(label="Episode Rate", value=0.1)

                gr.Markdown("#### Output")
                tr_output_dir = gr.Textbox(label="Output Directory", value="./outputs")
                tr_use_wandb = gr.Checkbox(label="Log to W&B", value=False)

                # ── B2: Advanced Training Config Accordion ──
                with gr.Accordion("Advanced", open=False):
                    gr.Markdown("##### Distributed")
                    with gr.Row():
                        adv_deepspeed_stage = gr.Dropdown(
                            label="DeepSpeed Stage",
                            choices=["1", "2", "3"],
                            value="2",
                        )
                        adv_num_gpus = gr.Number(label="Num GPUs", value=1, precision=0)
                        adv_gradient_checkpointing = gr.Checkbox(
                            label="Gradient Checkpointing", value=False
                        )

                    gr.Markdown("##### Optimization")
                    with gr.Row():
                        adv_optimizer = gr.Dropdown(
                            label="Optimizer",
                            choices=[
                                "adamw_torch_fused",
                                "adamw_torch",
                                "adafactor",
                                "paged_adamw_8bit",
                            ],
                            value="adamw_torch_fused",
                        )
                        adv_lr_scheduler = gr.Dropdown(
                            label="LR Scheduler",
                            choices=["cosine", "linear", "polynomial"],
                            value="cosine",
                        )
                    with gr.Row():
                        adv_max_grad_norm = gr.Number(label="Max Grad Norm", value=1.0)
                        adv_gradient_accum = gr.Number(
                            label="Gradient Accumulation Steps", value=1, precision=0
                        )

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
                        adv_random_rotation = gr.Number(label="Random Rotation Angle", value=0, precision=0)

                    gr.Markdown("##### Saving & Other")
                    with gr.Row():
                        adv_save_total_limit = gr.Number(label="Save Total Limit", value=5, precision=0)
                        adv_state_dropout = gr.Number(label="State Dropout", value=0.0)
                    with gr.Row():
                        adv_dataloader_workers = gr.Number(label="Dataloader Workers", value=4, precision=0)
                        adv_enable_profiling = gr.Checkbox(label="Enable PyTorch Profiler", value=False)

                with gr.Row():
                    tr_launch_btn = gr.Button("Launch Training", variant="primary")
                    tr_stop_btn = gr.Button("Stop Training", variant="stop")
                tr_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("---")

                # ── B1: Resume from Checkpoint ──
                gr.Markdown("#### Resume Training")
                tr_resume_ckpt = gr.Textbox(
                    label="Checkpoint Path",
                    placeholder="/path/to/outputs/checkpoint-5000",
                )
                tr_resume_btn = gr.Button("Resume Training", variant="primary", size="sm")

            # ── Right: Monitoring ──
            with gr.Column(scale=1):
                gr.Markdown("### Active Run Monitor")

                # Track the current run_id
                current_run_id = gr.State(value="")

                tr_log = gr.Textbox(label="Training Log", lines=18, interactive=False)
                tr_loss_plot = gr.Plot(label="Loss Curve")
                tr_checkpoints = gr.Dataframe(
                    headers=["Checkpoint", "Step"],
                    label="Saved Checkpoints",
                    interactive=False,
                )

                gr.Markdown("#### Register Checkpoint as Model")
                with gr.Row():
                    ckpt_path = gr.Textbox(
                        label="Checkpoint Path",
                        placeholder="Paste from checkpoints above",
                    )
                    ckpt_name = gr.Textbox(
                        label="Model Name",
                        placeholder="my-model-v1",
                    )
                reg_ckpt_btn = gr.Button("Register as Model", size="sm")
                reg_ckpt_status = gr.Textbox(label="", interactive=False)

        gr.Markdown("---")

        # ── Run History ──
        gr.Markdown("### Run History")
        run_table = gr.Dataframe(
            headers=["Run ID", "Dataset", "Status", "Loss", "Step", "Started"],
            label="Training Runs",
            interactive=False,
            value=_run_history_table(store, None),
        )
        refresh_runs_btn = gr.Button("Refresh", size="sm")

        # ── Callbacks ──

        def _build_training_cmd(
            dataset, base_model, embodiment, tune_llm, tune_visual,
            tune_projector, tune_diffusion, lr, max_steps, batch_size,
            weight_decay, warmup_ratio, save_steps, shard_size,
            episode_rate, output_dir, use_wandb,
            # Advanced params
            deepspeed_stage, num_gpus, gradient_checkpointing,
            optimizer, lr_scheduler, max_grad_norm, gradient_accum,
            bf16, fp16, tf32, eval_enable, eval_steps, eval_split_ratio,
            color_jitter, brightness, contrast, saturation, hue,
            random_rotation, save_total_limit, state_dropout,
            dataloader_workers, enable_profiling,
            resume_ckpt_path=None,
        ) -> tuple[dict, list[str]]:
            """Build the config dict and command list for a training run."""
            config = {
                "base_model": base_model,
                "dataset_path": dataset,
                "embodiment_tag": embodiment,
                "tune_llm": tune_llm,
                "tune_visual": tune_visual,
                "tune_projector": tune_projector,
                "tune_diffusion": tune_diffusion,
                "learning_rate": lr,
                "max_steps": int(max_steps),
                "global_batch_size": int(batch_size),
                "weight_decay": weight_decay,
                "warmup_ratio": warmup_ratio,
                "save_steps": int(save_steps),
                "shard_size": int(shard_size),
                "episode_sampling_rate": episode_rate,
                "output_dir": output_dir,
                "use_wandb": use_wandb,
                # Advanced
                "deepspeed_stage": int(deepspeed_stage),
                "num_gpus": int(num_gpus),
                "gradient_checkpointing": gradient_checkpointing,
                "optimizer": optimizer,
                "lr_scheduler_type": lr_scheduler,
                "max_grad_norm": max_grad_norm,
                "gradient_accumulation_steps": int(gradient_accum),
                "bf16": bf16,
                "fp16": fp16,
                "tf32": tf32,
                "eval_enabled": eval_enable,
                "eval_steps": int(eval_steps),
                "eval_split_ratio": eval_split_ratio,
                "color_jitter": color_jitter,
                "color_jitter_brightness": brightness,
                "color_jitter_contrast": contrast,
                "color_jitter_saturation": saturation,
                "color_jitter_hue": hue,
                "random_rotation_angle": int(random_rotation),
                "save_total_limit": int(save_total_limit),
                "state_dropout_prob": state_dropout,
                "dataloader_num_workers": int(dataloader_workers),
                "enable_profiling": enable_profiling,
            }
            if resume_ckpt_path:
                config["resume_checkpoint_path"] = resume_ckpt_path

            venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
            cmd = [
                venv_python,
                "-m", "gr00t.experiment.launch_finetune",
                "--base_model_path", base_model,
                "--dataset_path", dataset,
                "--embodiment_tag", embodiment,
                "--learning_rate", str(lr),
                "--max_steps", str(int(max_steps)),
                "--global_batch_size", str(int(batch_size)),
                "--weight_decay", str(weight_decay),
                "--warmup_ratio", str(warmup_ratio),
                "--save_steps", str(int(save_steps)),
                "--shard_size", str(int(shard_size)),
                "--episode_sampling_rate", str(episode_rate),
                "--output_dir", output_dir,
            ]

            if tune_llm:
                cmd.append("--tune_llm")
            if tune_visual:
                cmd.append("--tune_visual")
            if not tune_projector:
                cmd.append("--no-tune_projector")
            if not tune_diffusion:
                cmd.append("--no-tune_diffusion_model")
            if use_wandb:
                cmd.append("--use_wandb")

            # Advanced args
            cmd.extend(["--num_gpus", str(int(num_gpus))])
            cmd.extend(["--gradient_accumulation_steps", str(int(gradient_accum))])
            cmd.extend(["--save_total_limit", str(int(save_total_limit))])
            cmd.extend(["--dataloader_num_workers", str(int(dataloader_workers))])

            if int(deepspeed_stage) != 2:
                cmd.extend(["--deepspeed_stage", str(int(deepspeed_stage))])
            if gradient_checkpointing:
                cmd.append("--gradient_checkpointing")
            if optimizer != "adamw_torch_fused":
                cmd.extend(["--optim", optimizer])
            if lr_scheduler != "cosine":
                cmd.extend(["--lr_scheduler_type", lr_scheduler])

            if color_jitter:
                cmd.extend([
                    "--color_jitter_params",
                    "brightness", str(brightness),
                    "contrast", str(contrast),
                    "saturation", str(saturation),
                    "hue", str(hue),
                ])

            if int(random_rotation) > 0:
                cmd.extend(["--random_rotation_angle", str(int(random_rotation))])
            if state_dropout > 0:
                cmd.extend(["--state_dropout_prob", str(state_dropout)])
            if enable_profiling:
                cmd.append("--enable_profiling")

            if eval_enable:
                cmd.extend(["--eval_strategy", "steps"])
                cmd.extend(["--eval_steps", str(int(eval_steps))])

            # Resume: set output_dir to the checkpoint's parent to let HF Trainer auto-detect
            if resume_ckpt_path:
                ckpt_parent = str(Path(resume_ckpt_path).parent)
                # Override output_dir to the same dir so Trainer finds the checkpoint
                replaced = False
                for i, arg in enumerate(cmd):
                    if arg == "--output_dir" and i + 1 < len(cmd):
                        cmd[i + 1] = ckpt_parent
                        replaced = True
                        break
                if not replaced:
                    cmd.extend(["--output_dir", ckpt_parent])
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
            dataloader_workers, enable_profiling,
            proj,
        ):
            if not dataset.strip():
                return "Error: dataset_path is required", ""

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

            run_id = store.create_run(
                project_id=pid,
                run_type="training",
                config=config,
                dataset_id=None,
            )

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
            dataloader_workers, enable_profiling,
            proj,
        ):
            if not resume_ckpt_path.strip():
                return "Error: checkpoint path is required", ""
            if not dataset.strip():
                return "Error: dataset_path is required", ""

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

            run_id = store.create_run(
                project_id=pid,
                run_type="training",
                config=config,
                dataset_id=None,
            )

            msg = task_runner.launch(run_id, cmd, cwd=project_root)
            return msg, run_id

        def stop_training(run_id):
            if not run_id:
                return "No active training run"
            return task_runner.stop(run_id)

        def refresh_log(run_id):
            if not run_id:
                return ""
            return task_runner.tail_log(run_id, 50)

        def refresh_loss_plot(run_id):
            if not run_id:
                return None
            log_text = task_runner.tail_log(run_id, 500)
            steps = []
            losses = []
            for line in log_text.splitlines():
                m = re.search(r"'loss':\s*([\d.e+-]+).*'step':\s*(\d+)", line)
                if m:
                    losses.append(float(m.group(1)))
                    steps.append(int(m.group(2)))
            if not steps:
                return None
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots(figsize=(8, 4))
                ax.plot(steps, losses, "b-", linewidth=1)
                ax.set_xlabel("Step")
                ax.set_ylabel("Loss")
                ax.set_title("Training Loss")
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                return fig
            except Exception:
                return None

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
                    step = step_m.group(1) if step_m else "?"
                    rows.append([ckpt, step])
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
                project_id=pid,
                name=name,
                path=path,
                embodiment_tag=project["embodiment_tag"] if project else "new_embodiment",
                step=step,
                base_model=project["base_model"] if project else "nvidia/GR00T-N1.6-3B",
            )
            return f"Model registered: {mid}"

        # All inputs shared between launch and resume
        _shared_inputs = [
            tr_dataset, tr_base_model, tr_embodiment,
            tr_tune_llm, tr_tune_visual, tr_tune_projector, tr_tune_diffusion,
            tr_lr, tr_max_steps, tr_batch_size, tr_weight_decay,
            tr_warmup_ratio, tr_save_steps, tr_shard_size,
            tr_episode_rate, tr_output_dir, tr_use_wandb,
            # Advanced
            adv_deepspeed_stage, adv_num_gpus, adv_gradient_checkpointing,
            adv_optimizer, adv_lr_scheduler, adv_max_grad_norm, adv_gradient_accum,
            adv_bf16, adv_fp16, adv_tf32,
            adv_eval_enable, adv_eval_steps, adv_eval_split_ratio,
            adv_color_jitter, adv_brightness, adv_contrast, adv_saturation, adv_hue,
            adv_random_rotation, adv_save_total_limit, adv_state_dropout,
            adv_dataloader_workers, adv_enable_profiling,
        ]

        tr_launch_btn.click(
            launch_training,
            inputs=_shared_inputs + [project_state],
            outputs=[tr_status, current_run_id],
        )
        tr_resume_btn.click(
            resume_training,
            inputs=[tr_resume_ckpt] + _shared_inputs + [project_state],
            outputs=[tr_status, current_run_id],
        )
        tr_stop_btn.click(
            stop_training,
            inputs=[current_run_id],
            outputs=[tr_status],
        )

        reg_ckpt_btn.click(
            register_checkpoint,
            inputs=[ckpt_path, ckpt_name, project_state],
            outputs=[reg_ckpt_status],
        )
        refresh_runs_btn.click(
            refresh_runs, inputs=[project_state], outputs=[run_table]
        )

        tr_timer = gr.Timer(5)
        tr_timer.tick(refresh_log, inputs=[current_run_id], outputs=[tr_log])
        tr_timer.tick(refresh_loss_plot, inputs=[current_run_id], outputs=[tr_loss_plot])
        tr_timer.tick(refresh_checkpoints, inputs=[current_run_id], outputs=[tr_checkpoints])
