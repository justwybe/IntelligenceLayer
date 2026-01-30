from __future__ import annotations

"""Evaluate tab — open-loop eval, simulation rollout, model comparison.

All evaluation runs are tracked in the DB via TaskRunner.
"""

import glob
import json
import os
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

SIM_TASKS = {
    "LIBERO": [
        "libero/libero_panda/KITCHEN_SCENE1_open_the_bottom_drawer_of_the_cabinet",
        "libero/libero_panda/KITCHEN_SCENE2_put_the_black_bowl_on_the_plate",
        "libero/libero_panda/KITCHEN_SCENE3_turn_on_the_stove",
        "libero/libero_panda/KITCHEN_SCENE4_put_the_wine_bottle_on_top_of_the_cabinet",
        "libero/libero_panda/KITCHEN_SCENE6_put_the_yellow_and_white_mug_to_the_front_of_the_coffee_machine",
        "libero/libero_panda/KITCHEN_SCENE9_put_the_frying_pan_on_the_stove",
        "libero/libero_panda/KITCHEN_SCENE10_put_the_chocolate_pudding_to_the_top_shelf_of_the_middle",
        "libero/libero_panda/LIVING_ROOM_SCENE1_pick_up_the_ketchup_and_put_it_in_the_basket",
        "libero/libero_panda/LIVING_ROOM_SCENE2_pick_up_the_red_mug_and_put_it_to_the_left_of_the_plate",
        "libero/libero_panda/LIVING_ROOM_SCENE6_put_the_white_mug_on_the_left_plate",
    ],
    "SimplerEnv": [
        "simpler_env/google_robot/PickCoke-v0",
        "simpler_env/widowx/StackGreenCubeOnYellowCubeBakedTexInScene-v0",
    ],
    "BEHAVIOR": [
        "sim_behavior_r1_pro/BehaviorR1ProBimanualHangGarment-v0",
        "sim_behavior_r1_pro/BehaviorR1ProBimanualSortBooks-v0",
    ],
}


def _model_dropdown_choices(store: WorkspaceStore, project_id: str | None) -> list[str]:
    models = store.list_models(project_id=project_id)
    choices = []
    for m in models:
        choices.append(f"{m['name']} | {m['path']}")
    return choices


def _eval_history_table(store: WorkspaceStore, project_id: str | None) -> list[list]:
    runs = store.list_runs(project_id=project_id)
    eval_runs = [r for r in runs if r["run_type"] in ("evaluation", "simulation", "benchmark")]
    if not eval_runs:
        return [["No evaluation runs", "", "", "", ""]]
    rows = []
    for r in eval_runs:
        metrics = {}
        try:
            if r.get("metrics"):
                metrics = json.loads(r["metrics"]) if isinstance(r["metrics"], str) else r["metrics"]
        except Exception:
            pass
        metrics_str = ", ".join(f"{k}={v}" for k, v in list(metrics.items())[:3]) if metrics else "-"
        rows.append([
            r["id"][:8],
            r["run_type"],
            r["status"],
            metrics_str,
            r.get("started_at", "")[:16] if r.get("started_at") else "",
        ])
    return rows


def create_evaluate_tab(
    store: WorkspaceStore,
    task_runner: TaskRunner,
    project_state: gr.State,
    project_root: str,
):
    with gr.Tab("Evaluate"):
        gr.Markdown("## Evaluate")

        with gr.Tabs():
            # ── Sub-tab 1: Open-Loop Evaluation ──
            with gr.Tab("Open-Loop Eval"):
                gr.Markdown(
                    "Run open-loop evaluation comparing predicted vs ground-truth actions."
                )

                # Track current eval run
                ol_run_id = gr.State(value="")

                with gr.Row():
                    with gr.Column():
                        ol_dataset_path = gr.Textbox(
                            label="Dataset Path",
                            placeholder="demo_data/cube_to_bowl_5/",
                            value="demo_data/cube_to_bowl_5/",
                        )
                        ol_model_path = gr.Textbox(
                            label="Model Path",
                            placeholder="nvidia/GR00T-N1.6-3B",
                        )
                        ol_embodiment = gr.Dropdown(
                            label="Embodiment Tag",
                            choices=EMBODIMENT_CHOICES,
                            value="new_embodiment",
                        )
                        ol_traj_ids = gr.Textbox(
                            label="Trajectory IDs (comma-separated)",
                            value="0",
                        )
                        with gr.Row():
                            ol_steps = gr.Number(label="Max Steps", value=200, precision=0)
                            ol_action_horizon = gr.Number(
                                label="Action Horizon", value=16, precision=0
                            )
                        with gr.Row():
                            ol_launch_btn = gr.Button("Run Eval", variant="primary")
                            ol_stop_btn = gr.Button("Stop")

                    with gr.Column():
                        ol_status = gr.Textbox(label="Status", interactive=False)
                        ol_log = gr.Textbox(label="Log Output", lines=12, interactive=False)
                        ol_gallery = gr.Gallery(
                            label="Trajectory Plots",
                            columns=2,
                            height="auto",
                        )
                        ol_metrics = gr.Dataframe(
                            headers=["Trajectory", "MSE", "MAE"],
                            label="Metrics",
                            interactive=False,
                        )

                # Derive eval output dir from WYBE_DATA_DIR
                _eval_base = os.path.join(
                    os.environ.get("WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio")),
                    "eval_outputs",
                )

                def launch_open_loop(dataset_path, model_path, embodiment, traj_ids_str, steps, action_horizon, proj):
                    pid = proj.get("id") if proj else None
                    if not pid:
                        return "Select a project first", ""

                    config = {
                        "dataset_path": dataset_path,
                        "model_path": model_path,
                        "embodiment_tag": embodiment,
                        "traj_ids": traj_ids_str,
                        "steps": int(steps),
                        "action_horizon": int(action_horizon),
                    }
                    run_id = store.create_run(
                        project_id=pid,
                        run_type="evaluation",
                        config=config,
                    )

                    save_dir = os.path.join(_eval_base, run_id)
                    os.makedirs(save_dir, exist_ok=True)

                    venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
                    cmd = [
                        venv_python,
                        "-m", "gr00t.eval.open_loop_eval",
                        "--dataset_path", dataset_path,
                        "--embodiment_tag", embodiment,
                        "--steps", str(int(steps)),
                        "--action_horizon", str(int(action_horizon)),
                        "--save_plot_path", f"{save_dir}/traj.jpeg",
                    ]

                    try:
                        ids = [int(x.strip()) for x in traj_ids_str.split(",") if x.strip()]
                        for tid in ids:
                            cmd.extend(["--traj_ids", str(tid)])
                    except ValueError:
                        return "Invalid trajectory IDs", ""

                    if model_path.strip():
                        cmd.extend(["--model_path", model_path.strip()])

                    msg = task_runner.launch(run_id, cmd, cwd=project_root)
                    return msg, run_id

                def stop_open_loop(run_id):
                    if not run_id:
                        return "No active eval run"
                    return task_runner.stop(run_id)

                def refresh_ol_log(run_id):
                    return task_runner.tail_log(run_id, 40) if run_id else ""

                def refresh_ol_status(run_id):
                    return task_runner.status(run_id) if run_id else ""

                def refresh_ol_gallery(run_id):
                    if not run_id:
                        return []
                    save_dir = os.path.join(_eval_base, run_id)
                    images = sorted(glob.glob(f"{save_dir}/*.jpeg")) + sorted(
                        glob.glob(f"{save_dir}/*.png")
                    )
                    return images if images else []

                def refresh_ol_metrics(run_id):
                    if not run_id:
                        return []
                    log_text = task_runner.tail_log(run_id, 200)
                    rows = []
                    for line in log_text.splitlines():
                        m = re.search(
                            r"MSE for trajectory (\d+): ([\d.e+-]+), MAE: ([\d.e+-]+)",
                            line,
                        )
                        if m:
                            rows.append([int(m.group(1)), float(m.group(2)), float(m.group(3))])
                    return rows if rows else []

                ol_launch_btn.click(
                    launch_open_loop,
                    inputs=[ol_dataset_path, ol_model_path, ol_embodiment, ol_traj_ids, ol_steps, ol_action_horizon, project_state],
                    outputs=[ol_status, ol_run_id],
                )
                ol_stop_btn.click(stop_open_loop, inputs=[ol_run_id], outputs=[ol_status])

                ol_timer = gr.Timer(3)
                ol_timer.tick(refresh_ol_log, inputs=[ol_run_id], outputs=[ol_log])
                ol_timer.tick(refresh_ol_status, inputs=[ol_run_id], outputs=[ol_status])
                ol_timer.tick(refresh_ol_gallery, inputs=[ol_run_id], outputs=[ol_gallery])
                ol_timer.tick(refresh_ol_metrics, inputs=[ol_run_id], outputs=[ol_metrics])

            # ── Sub-tab 2: Simulation Rollout ──
            with gr.Tab("Simulation"):
                gr.Markdown("Launch simulation environments and evaluate policies.")

                sim_run_id = gr.State(value="")

                with gr.Row():
                    with gr.Column():
                        sim_env = gr.Radio(
                            label="Environment",
                            choices=["LIBERO", "SimplerEnv", "BEHAVIOR"],
                            value="LIBERO",
                        )
                        sim_task = gr.Dropdown(
                            label="Task",
                            choices=SIM_TASKS["LIBERO"],
                            value=SIM_TASKS["LIBERO"][0] if SIM_TASKS["LIBERO"] else "",
                        )
                        sim_model_path = gr.Textbox(
                            label="Model Path (blank = use server)",
                            placeholder="nvidia/GR00T-N1.6-3B",
                        )
                        with gr.Row():
                            sim_use_server = gr.Checkbox(label="Use Policy Server", value=False)
                            sim_server_host = gr.Textbox(
                                label="Host", value="localhost", visible=False
                            )
                            sim_server_port = gr.Number(
                                label="Port", value=5555, precision=0, visible=False
                            )
                        with gr.Row():
                            sim_max_steps = gr.Number(label="Max Steps", value=504, precision=0)
                            sim_n_action_steps = gr.Number(label="N Action Steps", value=8, precision=0)
                        with gr.Row():
                            sim_n_episodes = gr.Number(label="N Episodes", value=10, precision=0)
                            sim_n_envs = gr.Number(label="N Envs", value=1, precision=0)
                        with gr.Row():
                            sim_launch_btn = gr.Button("Launch Simulation", variant="primary")
                            sim_stop_btn = gr.Button("Stop")

                    with gr.Column():
                        sim_status = gr.Textbox(label="Status", interactive=False)
                        sim_log = gr.Textbox(label="Log Output", lines=15, interactive=False)
                        sim_video = gr.Video(label="Recorded Episode")
                        sim_metrics = gr.Dataframe(
                            headers=["Metric", "Value"],
                            label="Results",
                            interactive=False,
                        )

                def update_tasks(env_name):
                    tasks = SIM_TASKS.get(env_name, [])
                    return gr.update(choices=tasks, value=tasks[0] if tasks else "")

                def toggle_server_fields(use_server):
                    return gr.update(visible=use_server), gr.update(visible=use_server)

                def launch_sim(
                    env_name, task, model_path, use_server, server_host, server_port,
                    max_steps, n_action_steps, n_episodes, n_envs, proj,
                ):
                    pid = proj.get("id") if proj else None
                    if not pid:
                        return "Select a project first", ""

                    config = {
                        "env_name": env_name,
                        "task": task,
                        "model_path": model_path,
                        "use_server": use_server,
                        "max_steps": int(max_steps),
                        "n_action_steps": int(n_action_steps),
                        "n_episodes": int(n_episodes),
                        "n_envs": int(n_envs),
                    }
                    run_id = store.create_run(
                        project_id=pid,
                        run_type="simulation",
                        config=config,
                    )

                    venv_python = str(Path(project_root) / ".venv" / "bin" / "python")
                    if env_name == "BEHAVIOR":
                        # BEHAVIOR may require a separate conda env; fall back to venv if available
                        python_cmd = venv_python if Path(venv_python).exists() else "python3"
                    else:
                        python_cmd = venv_python

                    cmd = [
                        python_cmd,
                        "-m", "gr00t.eval.rollout_policy",
                        "--env_name", task,
                        "--max_episode_steps", str(int(max_steps)),
                        "--n_action_steps", str(int(n_action_steps)),
                        "--n_episodes", str(int(n_episodes)),
                        "--n_envs", str(int(n_envs)),
                    ]

                    if use_server:
                        cmd.extend([
                            "--policy_client_host", server_host,
                            "--policy_client_port", str(int(server_port)),
                        ])
                    else:
                        if not model_path.strip():
                            return "Provide a model_path or check 'Use Policy Server'", ""
                        cmd.extend(["--model_path", model_path.strip()])

                    msg = task_runner.launch(run_id, cmd, cwd=project_root)
                    return msg, run_id

                def stop_sim(run_id):
                    if not run_id:
                        return "No active simulation run"
                    return task_runner.stop(run_id)

                def refresh_sim_log(run_id):
                    return task_runner.tail_log(run_id, 40) if run_id else ""

                def refresh_sim_status(run_id):
                    return task_runner.status(run_id) if run_id else ""

                def refresh_sim_video(run_id):
                    # Video output path is controlled by gr00t.eval.rollout_policy defaults
                    for pattern in ["/tmp/sim_eval_videos_*/*.mp4", "/tmp/sim_eval_videos_*/*.avi"]:
                        videos = sorted(glob.glob(pattern), key=os.path.getmtime)
                        if videos:
                            return videos[-1]
                    return None

                def refresh_sim_metrics(run_id):
                    if not run_id:
                        return []
                    log_text = task_runner.tail_log(run_id, 200)
                    rows = []
                    m = re.search(r"success rate:\s*([\d.]+)", log_text)
                    if m:
                        rows.append(["Success Rate", m.group(1)])
                    m = re.search(r"Collecting \d+ episodes took ([\d.]+) seconds", log_text)
                    if m:
                        rows.append(["Total Time (s)", m.group(1)])
                    return rows if rows else []

                sim_env.change(update_tasks, inputs=[sim_env], outputs=[sim_task])
                sim_use_server.change(
                    toggle_server_fields,
                    inputs=[sim_use_server],
                    outputs=[sim_server_host, sim_server_port],
                )
                sim_launch_btn.click(
                    launch_sim,
                    inputs=[
                        sim_env, sim_task, sim_model_path, sim_use_server,
                        sim_server_host, sim_server_port, sim_max_steps,
                        sim_n_action_steps, sim_n_episodes, sim_n_envs, project_state,
                    ],
                    outputs=[sim_status, sim_run_id],
                )
                sim_stop_btn.click(stop_sim, inputs=[sim_run_id], outputs=[sim_status])

                sim_timer = gr.Timer(3)
                sim_timer.tick(refresh_sim_log, inputs=[sim_run_id], outputs=[sim_log])
                sim_timer.tick(refresh_sim_status, inputs=[sim_run_id], outputs=[sim_status])
                sim_timer.tick(refresh_sim_video, inputs=[sim_run_id], outputs=[sim_video])
                sim_timer.tick(refresh_sim_metrics, inputs=[sim_run_id], outputs=[sim_metrics])

            # ── Sub-tab 3: Model Comparison ──
            with gr.Tab("Compare Models"):
                gr.Markdown("Compare evaluation metrics across models.")

                compare_btn = gr.Button("Load Comparison", variant="primary", size="sm")
                compare_table = gr.Dataframe(
                    headers=["Model", "Eval Type", "Metrics"],
                    label="Model Evaluations",
                    interactive=False,
                )
                compare_plot = gr.Plot(label="Comparison Chart")

                def load_comparison(proj):
                    pid = proj.get("id") if proj else None
                    models = store.list_models(project_id=pid)
                    rows = []
                    all_metrics = []
                    for m in models:
                        evals = store.list_evaluations(model_id=m["id"])
                        if not evals:
                            rows.append([m["name"], "-", "No evaluations"])
                            continue
                        for ev in evals:
                            try:
                                metrics = json.loads(ev["metrics"]) if isinstance(ev["metrics"], str) else ev["metrics"]
                            except Exception:
                                metrics = {}
                            metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
                            rows.append([m["name"], ev.get("eval_type", "-"), metrics_str])
                            all_metrics.append({"model": m["name"], **metrics})

                    if not rows:
                        rows = [["No models found", "", ""]]

                    # Build comparison plot
                    fig = None
                    if len(all_metrics) >= 2:
                        try:
                            import matplotlib
                            matplotlib.use("Agg")
                            import matplotlib.pyplot as plt

                            # Find common numeric metric keys
                            numeric_keys = set()
                            for m in all_metrics:
                                for k, v in m.items():
                                    if k != "model" and isinstance(v, (int, float)):
                                        numeric_keys.add(k)

                            if numeric_keys:
                                fig, ax = plt.subplots(figsize=(8, 4))
                                model_names = [m["model"] for m in all_metrics]
                                x = range(len(model_names))
                                width = 0.8 / max(len(numeric_keys), 1)
                                for i, key in enumerate(sorted(numeric_keys)):
                                    values = [m.get(key, 0) for m in all_metrics]
                                    offset = (i - len(numeric_keys) / 2) * width
                                    ax.bar([xi + offset for xi in x], values, width, label=key)
                                ax.set_xticks(list(x))
                                ax.set_xticklabels(model_names, rotation=45, ha="right")
                                ax.legend()
                                ax.set_title("Model Comparison")
                                plt.tight_layout()
                        except Exception:
                            pass

                    return rows, fig

                compare_btn.click(
                    load_comparison,
                    inputs=[project_state],
                    outputs=[compare_table, compare_plot],
                )

        gr.Markdown("---")

        # ── Evaluation History ──
        gr.Markdown("### Evaluation History")
        eval_table = gr.Dataframe(
            headers=["Run ID", "Type", "Status", "Metrics", "Started"],
            label="All Evaluation Runs",
            interactive=False,
            value=_eval_history_table(store, None),
        )
        refresh_eval_btn = gr.Button("Refresh", size="sm")

        def refresh_evals(proj):
            pid = proj.get("id") if proj else None
            return _eval_history_table(store, pid)

        refresh_eval_btn.click(
            refresh_evals, inputs=[project_state], outputs=[eval_table]
        )
