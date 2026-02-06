"""Training constants endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import require_auth
from api.schemas.training import TrainingConstantsResponse, TrainingPreset
from frontend.constants import (
    EMBODIMENT_CHOICES,
    ISAAC_LAB_ENVS,
    RL_ALGORITHMS,
    TRAINING_PRESETS,
)

router = APIRouter(
    prefix="/api/training",
    tags=["training"],
    dependencies=[Depends(require_auth)],
)

OPTIMIZER_CHOICES = [
    "adamw_torch_fused",
    "adamw_torch",
    "adafactor",
    "paged_adamw_8bit",
]
LR_SCHEDULER_CHOICES = ["cosine", "linear", "polynomial"]
DEEPSPEED_STAGES = ["1", "2", "3"]


@router.get("/constants", response_model=TrainingConstantsResponse)
async def get_training_constants() -> TrainingConstantsResponse:
    return TrainingConstantsResponse(
        presets={k: TrainingPreset(**v) for k, v in TRAINING_PRESETS.items()},
        embodiment_choices=list(EMBODIMENT_CHOICES),
        isaac_lab_envs=list(ISAAC_LAB_ENVS),
        rl_algorithms=list(RL_ALGORITHMS),
        optimizer_choices=OPTIMIZER_CHOICES,
        lr_scheduler_choices=LR_SCHEDULER_CHOICES,
        deepspeed_stages=DEEPSPEED_STAGES,
    )
