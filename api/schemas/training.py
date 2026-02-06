"""Pydantic models for training and model endpoints."""

from __future__ import annotations

from pydantic import BaseModel


# ── Training Constants ────────────────────────────────────────────────

class TrainingPreset(BaseModel):
    learning_rate: float
    max_steps: int
    global_batch_size: int
    weight_decay: float
    warmup_ratio: float
    save_steps: int
    shard_size: int
    episode_sampling_rate: float


class TrainingConstantsResponse(BaseModel):
    presets: dict[str, TrainingPreset]
    embodiment_choices: list[str]
    isaac_lab_envs: list[str]
    rl_algorithms: list[str]
    optimizer_choices: list[str]
    lr_scheduler_choices: list[str]
    deepspeed_stages: list[str]


# ── Training Metrics ──────────────────────────────────────────────────

class LossPoint(BaseModel):
    step: int
    loss: float


class CheckpointInfo(BaseModel):
    path: str
    step: int | None = None


class TrainingMetricsResponse(BaseModel):
    loss_curve: list[LossPoint]
    checkpoints: list[CheckpointInfo]
    current_step: int
    max_steps: int
    progress_pct: float
    status: str


# ── Models ────────────────────────────────────────────────────────────

class ModelCreate(BaseModel):
    name: str
    path: str
    source_run_id: str | None = None
    base_model: str | None = None
    embodiment_tag: str | None = None
    step: int | None = None
    notes: str = ""


class ModelResponse(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    path: str
    source_run_id: str | None = None
    base_model: str | None = None
    embodiment_tag: str | None = None
    step: int | None = None
    created_at: str
    notes: str | None = None


class ModelList(BaseModel):
    models: list[ModelResponse]
