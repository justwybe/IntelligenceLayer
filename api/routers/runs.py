"""Run management endpoints — launch, poll, stop."""

from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import require_auth
from api.deps import get_project_root, get_store, get_task_runner
from api.schemas.datasets import RunCreate, RunList, RunResponse, RunStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/runs",
    tags=["runs"],
    dependencies=[Depends(require_auth)],
)


def _build_cmd(run_type: str, config: dict, project_root: str) -> list[str]:
    """Build the subprocess command for a given run type."""
    venv_python = os.path.join(project_root, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        import sys

        venv_python = sys.executable

    if run_type == "stats_computation":
        dataset_path = config.get("dataset_path", "")
        embodiment_tag = config.get("embodiment_tag", "new_embodiment")
        return [
            venv_python,
            "-m",
            "gr00t.data.stats",
            "--dataset-path",
            dataset_path,
            "--embodiment-tag",
            embodiment_tag,
        ]

    if run_type == "conversion":
        repo_id = config.get("repo_id", "")
        output_dir = config.get("output_dir", "")
        return [
            venv_python,
            "scripts/lerobot_conversion/convert_v3_to_v2.py",
            "--repo-id",
            repo_id,
            "--root",
            output_dir,
        ]

    raise HTTPException(status_code=400, detail=f"Unknown run type: {run_type}")


@router.get("", response_model=RunList)
async def list_runs(
    project_id: str | None = Query(None),
    run_type: str | None = Query(None),
    store=Depends(get_store),
) -> RunList:
    runs = store.list_runs(project_id=project_id, run_type=run_type)
    return RunList(runs=[RunResponse(**r) for r in runs])


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    body: RunCreate,
    project_id: str = Query(...),
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
    project_root: str = Depends(get_project_root),
) -> RunResponse:
    # Validate project exists
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create the run record
    run_id = store.create_run(
        project_id=project_id,
        run_type=body.run_type,
        config=body.config,
        dataset_id=body.dataset_id,
    )

    # Build command and launch
    cmd = _build_cmd(body.run_type, body.config, project_root)
    task_runner.launch(run_id, cmd, cwd=project_root)

    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to create run")
    return RunResponse(**run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, store=Depends(get_store)) -> RunResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(**run)


@router.get("/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
) -> RunStatusResponse:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    status = task_runner.status(run_id)
    log_tail = task_runner.tail_log(run_id, 80)
    return RunStatusResponse(status=status, log_tail=log_tail)


@router.post("/{run_id}/stop")
async def stop_run(
    run_id: str,
    store=Depends(get_store),
    task_runner=Depends(get_task_runner),
):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    msg = task_runner.stop(run_id)
    return {"message": msg}
