"""Project CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_auth
from api.deps import get_store
from api.schemas.projects import ProjectCreate, ProjectList, ProjectResponse

router = APIRouter(prefix="/api", tags=["projects"], dependencies=[Depends(require_auth)])


@router.get("/projects", response_model=ProjectList)
async def list_projects(store=Depends(get_store)) -> ProjectList:
    projects = store.list_projects()
    return ProjectList(projects=[ProjectResponse(**p) for p in projects])


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, store=Depends(get_store)) -> ProjectResponse:
    pid = store.create_project(
        name=body.name,
        embodiment_tag=body.embodiment_tag,
        base_model=body.base_model,
        notes=body.notes,
    )
    project = store.get_project(pid)
    if not project:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return ProjectResponse(**project)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, store=Depends(get_store)) -> ProjectResponse:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Add summary stats
    datasets = store.list_datasets(project_id)
    models = store.list_models(project_id)
    runs = store.list_runs(project_id)

    return ProjectResponse(
        **project,
        dataset_count=len(datasets),
        model_count=len(models),
        run_count=len(runs),
    )


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, store=Depends(get_store)):
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    store.delete_project(project_id)
