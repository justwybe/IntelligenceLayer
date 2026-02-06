"""Model registry endpoints — list, register, get."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import require_auth
from api.deps import get_store
from api.schemas.training import ModelCreate, ModelList, ModelResponse

router = APIRouter(
    prefix="/api/models",
    tags=["models"],
    dependencies=[Depends(require_auth)],
)


@router.get("", response_model=ModelList)
async def list_models(
    project_id: str | None = Query(None),
    store=Depends(get_store),
) -> ModelList:
    models = store.list_models(project_id=project_id)
    return ModelList(models=[ModelResponse(**m) for m in models])


@router.post("", response_model=ModelResponse, status_code=201)
async def register_model(
    body: ModelCreate,
    project_id: str = Query(...),
    store=Depends(get_store),
) -> ModelResponse:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    model_id = store.register_model(
        project_id=project_id,
        name=body.name,
        path=body.path,
        source_run_id=body.source_run_id,
        base_model=body.base_model,
        embodiment_tag=body.embodiment_tag,
        step=body.step,
        notes=body.notes,
    )

    model = store.get_model(model_id)
    if not model:
        raise HTTPException(status_code=500, detail="Failed to register model")
    return ModelResponse(**model)


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str, store=Depends(get_store)) -> ModelResponse:
    model = store.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse(**model)
