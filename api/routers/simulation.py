"""Simulation constants endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from api.schemas.simulation import SimulationConstantsResponse
from frontend.constants import EMBODIMENT_CHOICES, SIM_TASKS

router = APIRouter(
    prefix="/api/simulation",
    tags=["simulation"],
    dependencies=[Depends(require_auth)],
)


@router.get("/constants", response_model=SimulationConstantsResponse)
async def get_simulation_constants() -> SimulationConstantsResponse:
    return SimulationConstantsResponse(
        sim_tasks={k: list(v) for k, v in SIM_TASKS.items()},
        embodiment_choices=list(EMBODIMENT_CHOICES),
    )
