"""Pydantic models for simulation and evaluation endpoints."""

from __future__ import annotations

from pydantic import BaseModel


# ── Simulation Constants ─────────────────────────────────────────────

class SimulationConstantsResponse(BaseModel):
    sim_tasks: dict[str, list[str]]
    embodiment_choices: list[str]


# ── Eval Metrics ─────────────────────────────────────────────────────

class SimMetric(BaseModel):
    name: str
    value: str


class EvalMetric(BaseModel):
    trajectory: int
    mse: float
    mae: float


class EvalMetricsResponse(BaseModel):
    sim_metrics: list[SimMetric]
    eval_metrics: list[EvalMetric]


# ── Artifacts ────────────────────────────────────────────────────────

class ArtifactItem(BaseModel):
    filename: str
    url: str


class ArtifactList(BaseModel):
    artifacts: list[ArtifactItem]


# ── Evaluations ──────────────────────────────────────────────────────

class EvaluationResponse(BaseModel):
    id: str
    run_id: str
    model_id: str | None = None
    eval_type: str
    metrics: str | None = None
    artifacts: str | None = None
    created_at: str


class EvaluationList(BaseModel):
    evaluations: list[EvaluationResponse]


# ── Compare ──────────────────────────────────────────────────────────

class CompareEntry(BaseModel):
    model_name: str
    model_id: str
    eval_type: str
    metrics: dict


class CompareResponse(BaseModel):
    entries: list[CompareEntry]
