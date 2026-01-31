"""Shared constants for Wybe Studio — single source of truth."""

from __future__ import annotations

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

TRAINING_PRESETS: dict[str, dict] = {
    "Quick Start": {
        "learning_rate": 1e-4,
        "max_steps": 10000,
        "global_batch_size": 64,
        "weight_decay": 1e-5,
        "warmup_ratio": 0.05,
        "save_steps": 1000,
        "shard_size": 1024,
        "episode_sampling_rate": 0.1,
    },
    "Long Training": {
        "learning_rate": 5e-5,
        "max_steps": 50000,
        "global_batch_size": 64,
        "weight_decay": 1e-5,
        "warmup_ratio": 0.03,
        "save_steps": 5000,
        "shard_size": 1024,
        "episode_sampling_rate": 0.1,
    },
    "Quick Experiment": {
        "learning_rate": 2e-4,
        "max_steps": 2000,
        "global_batch_size": 32,
        "weight_decay": 1e-5,
        "warmup_ratio": 0.1,
        "save_steps": 500,
        "shard_size": 512,
        "episode_sampling_rate": 0.2,
    },
}

TEMPLATE_PROJECTS: list[dict] = [
    {
        "name": "Cube-to-Bowl Demo",
        "embodiment_tag": "new_embodiment",
        "base_model": "nvidia/GR00T-N1.6-3B",
        "description": "Pre-configured project with bundled cube_to_bowl demo data.",
        "demo_data_path": "demo_data/cube_to_bowl_5",
    },
]

ISAAC_LAB_ENVS: list[str] = [
    # Locomotion
    "Isaac-Velocity-Flat-Anymal-C-v0",
    "Isaac-Velocity-Rough-Anymal-C-v0",
    "Isaac-Velocity-Flat-Anymal-D-v0",
    "Isaac-Velocity-Rough-Anymal-D-v0",
    "Isaac-Velocity-Flat-Unitree-Go1-v0",
    "Isaac-Velocity-Rough-Unitree-Go1-v0",
    "Isaac-Velocity-Flat-Unitree-Go2-v0",
    "Isaac-Velocity-Rough-Unitree-Go2-v0",
    "Isaac-Velocity-Flat-H1-v0",
    "Isaac-Velocity-Rough-H1-v0",
    "Isaac-Velocity-Flat-G1-v0",
    "Isaac-Velocity-Rough-G1-v0",
    # Manipulation
    "Isaac-Lift-Cube-Franka-v0",
    "Isaac-Reach-Franka-v0",
    "Isaac-Stack-Cube-Franka-v0",
    "Isaac-Open-Drawer-Franka-v0",
    "Isaac-Repose-Cube-Shadow-OpenAI-FF-v0",
    "Isaac-Repose-Cube-Shadow-OpenAI-LSTM-v0",
    # Loco-Manipulation
    "Isaac-Navigation-Flat-Anymal-C-v0",
    "Isaac-Open-Drawer-Spot-v0",
]

RL_ALGORITHMS: list[str] = [
    "PPO",
    "SAC",
    "RSL-RL",
]

MIMIC_ENVS: list[str] = [
    "GR00T-Mimic-Cube-v0",
    "GR00T-Mimic-PickPlace-v0",
    "GR00T-Mimic-Stack-v0",
    "GR00T-Mimic-Kitchen-v0",
    "GR00T-Mimic-Drawer-v0",
]

SIM_TASKS: dict[str, list[str]] = {
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

# Activity feed rendering
EVENT_ICONS: dict[str, str] = {
    "project_created": "folder-plus",
    "dataset_registered": "database",
    "run_created": "play",
    "run_completed": "check-circle",
    "run_failed": "x-circle",
    "run_stopped": "stop-circle",
    "model_registered": "box",
    "server_started": "server",
    "server_stopped": "server",
    "evaluation_saved": "bar-chart",
}

EVENT_COLORS: dict[str, str] = {
    "project_created": "#22c55e",
    "dataset_registered": "#a855f7",
    "run_created": "#22c55e",
    "run_completed": "#4ade80",
    "run_failed": "#ef4444",
    "run_stopped": "#eab308",
    "model_registered": "#06b6d4",
    "server_started": "#4ade80",
    "server_stopped": "#ef4444",
    "evaluation_saved": "#22c55e",
}
