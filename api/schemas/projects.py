"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


# ── Projects ──────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    embodiment_tag: str
    base_model: str = "nvidia/GR00T-N1.6-3B"
    notes: str = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    embodiment_tag: str
    base_model: str
    created_at: str
    notes: str | None = None
    # Summary stats (optional, populated on detail endpoint)
    dataset_count: int | None = None
    model_count: int | None = None
    run_count: int | None = None


class ProjectList(BaseModel):
    projects: list[ProjectResponse]


# ── GPU ───────────────────────────────────────────────────────────────

class GPUInfo(BaseModel):
    name: str
    utilization_pct: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    power_w: float


class GPUResponse(BaseModel):
    gpus: list[GPUInfo]
    gpu_available: bool
    gpu_count: int


# ── Activity ──────────────────────────────────────────────────────────

class ActivityEntry(BaseModel):
    id: int
    project_id: str | None = None
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    message: str
    created_at: str


class ActivityList(BaseModel):
    entries: list[ActivityEntry]


# ── Health ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    gpu_available: bool
    gpu_count: int
    db_ok: bool
    uptime_seconds: float


# ── Server ────────────────────────────────────────────────────────────

class ServerInfo(BaseModel):
    model_path: str
    embodiment_tag: str
    port: int
    status: str
    alive: bool
