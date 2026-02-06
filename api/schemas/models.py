"""Pydantic models for model deploy, optimize, and benchmark endpoints."""

from __future__ import annotations

from pydantic import BaseModel


# ── Deploy ───────────────────────────────────────────────────────────

class DeployRequest(BaseModel):
    model_path: str
    embodiment_tag: str = "new_embodiment"
    port: int = 5555


class DeployResponse(BaseModel):
    message: str
    status: str


# ── Models Constants ─────────────────────────────────────────────────

class ModelsConstantsResponse(BaseModel):
    embodiment_choices: list[str]


# ── Benchmark Metrics ────────────────────────────────────────────────

class BenchmarkRow(BaseModel):
    device: str = ""
    mode: str = ""
    data_processing: str = ""
    backbone: str = ""
    action_head: str = ""
    e2e: str = ""
    frequency: str = ""


class BenchmarkMetricsResponse(BaseModel):
    rows: list[BenchmarkRow]
    status: str
