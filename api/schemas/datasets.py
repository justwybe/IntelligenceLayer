"""Pydantic models for dataset and run endpoints."""

from __future__ import annotations

from pydantic import BaseModel


# ── Datasets ─────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    name: str
    path: str
    source: str = "imported"


class DatasetResponse(BaseModel):
    id: str
    project_id: str | None = None
    name: str
    path: str
    source: str | None = None
    parent_dataset_id: str | None = None
    episode_count: int | None = None
    created_at: str
    metadata: str | None = None


class DatasetList(BaseModel):
    datasets: list[DatasetResponse]


# ── Episode Data ─────────────────────────────────────────────────────

class EpisodeRequest(BaseModel):
    dataset_path: str
    episode_index: int = 0


class TrajectoryTrace(BaseModel):
    name: str
    y: list[float]


class EpisodeDataResponse(BaseModel):
    video_path: str | None = None
    state_traces: list[TrajectoryTrace] = []
    action_traces: list[TrajectoryTrace] = []
    task_description: str = ""


# ── Inspect ──────────────────────────────────────────────────────────

class InspectRequest(BaseModel):
    dataset_path: str


class InspectResponse(BaseModel):
    info: str = ""
    modality: str = ""
    tasks: str = ""
    stats: str = ""


# ── Runs ─────────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    run_type: str
    config: dict
    dataset_id: str | None = None


class RunResponse(BaseModel):
    id: str
    project_id: str | None = None
    run_type: str
    dataset_id: str | None = None
    model_id: str | None = None
    config: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    log_path: str | None = None
    metrics: str | None = None
    pid: int | None = None


class RunList(BaseModel):
    runs: list[RunResponse]


class RunStatusResponse(BaseModel):
    status: str
    log_tail: str = ""


# ── Constants ────────────────────────────────────────────────────────

class ConstantsResponse(BaseModel):
    embodiment_choices: list[str]
    mimic_envs: list[str]
    source_options: list[str]
