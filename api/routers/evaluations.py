"""Evaluation listing and comparison endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, Query

from api.auth import require_auth
from api.deps import get_store
from api.schemas.simulation import (
    CompareEntry,
    CompareResponse,
    EvaluationList,
    EvaluationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/evaluations",
    tags=["evaluations"],
    dependencies=[Depends(require_auth)],
)


@router.get("", response_model=EvaluationList)
async def list_evaluations(
    model_id: str | None = Query(None),
    run_id: str | None = Query(None),
    store=Depends(get_store),
) -> EvaluationList:
    evals = store.list_evaluations(model_id=model_id, run_id=run_id)
    return EvaluationList(evaluations=[EvaluationResponse(**e) for e in evals])


@router.get("/compare", response_model=CompareResponse)
async def compare_models(
    project_id: str | None = Query(None),
    store=Depends(get_store),
) -> CompareResponse:
    models = store.list_models(project_id=project_id)
    entries: list[CompareEntry] = []

    for m in models:
        evals = store.list_evaluations(model_id=m["id"])
        for ev in evals:
            metrics: dict = {}
            try:
                raw = ev.get("metrics")
                if raw:
                    metrics = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                logger.debug("Failed to parse eval metrics", exc_info=True)
            entries.append(CompareEntry(
                model_name=m["name"],
                model_id=m["id"],
                eval_type=ev.get("eval_type", "unknown"),
                metrics=metrics,
            ))

    return CompareResponse(entries=entries)
