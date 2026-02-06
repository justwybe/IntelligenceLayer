"""Dataset management endpoints."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from api.auth import require_auth, verify_ws_token
from api.deps import get_project_root, get_store, validate_path_param
from api.schemas.datasets import (
    ConstantsResponse,
    DatasetCreate,
    DatasetList,
    DatasetResponse,
    EpisodeDataResponse,
    EpisodeRequest,
    InspectRequest,
    InspectResponse,
    TrajectoryTrace,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# Most endpoints require bearer auth
_auth = [Depends(require_auth)]


def _count_episodes(dataset_path: str) -> int | None:
    episodes_file = Path(dataset_path) / "meta" / "episodes.jsonl"
    if episodes_file.exists():
        return sum(1 for _ in episodes_file.open())
    return None


# ── CRUD ─────────────────────────────────────────────────────────────


@router.get("", response_model=DatasetList, dependencies=_auth)
async def list_datasets(
    project_id: str | None = Query(None),
    store=Depends(get_store),
) -> DatasetList:
    datasets = store.list_datasets(project_id=project_id)
    return DatasetList(datasets=[DatasetResponse(**d) for d in datasets])


@router.post("", response_model=DatasetResponse, status_code=201, dependencies=_auth)
async def create_dataset(
    body: DatasetCreate,
    project_id: str = Query(...),
    store=Depends(get_store),
) -> DatasetResponse:
    validate_path_param(body.path)
    episode_count = _count_episodes(body.path)
    did = store.register_dataset(
        project_id=project_id,
        name=body.name,
        path=body.path,
        source=body.source,
        episode_count=episode_count,
    )
    dataset = store.get_dataset(did)
    if not dataset:
        raise HTTPException(status_code=500, detail="Failed to create dataset")
    return DatasetResponse(**dataset)


@router.get("/constants", response_model=ConstantsResponse, dependencies=_auth)
async def get_constants() -> ConstantsResponse:
    from frontend.constants import EMBODIMENT_CHOICES, MIMIC_ENVS

    return ConstantsResponse(
        embodiment_choices=EMBODIMENT_CHOICES,
        mimic_envs=MIMIC_ENVS,
        source_options=["imported", "recorded", "mimic", "dreams", "urban_memory"],
    )


@router.get("/video", dependencies=[])
async def serve_video(
    path: str = Query(...),
    token: str = Query(""),
):
    """Serve video file with query-param auth (for <video> tags)."""
    if not verify_ws_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    validate_path_param(path, must_exist=True)
    video_path = Path(path)
    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    suffix = video_path.suffix.lower()
    media_types = {".mp4": "video/mp4", ".webm": "video/webm", ".avi": "video/x-msvideo"}
    media_type = media_types.get(suffix, "video/mp4")

    return FileResponse(str(video_path), media_type=media_type)


@router.get("/embodiment/{tag}", dependencies=_auth)
async def get_embodiment_config(tag: str, project_root: str = Depends(get_project_root)):
    """Return the modality config for an embodiment tag."""
    try:
        import sys

        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from gr00t.configs.data.embodiment_configs import MODALITY_CONFIGS
        from gr00t.data.utils import to_json_serializable

        cfg = MODALITY_CONFIGS.get(tag)
        if cfg is None:
            raise HTTPException(status_code=404, detail=f"No config for '{tag}'")
        serializable = {}
        for modality, mc in cfg.items():
            serializable[modality] = to_json_serializable(mc)
        return serializable
    except ImportError:
        raise HTTPException(status_code=501, detail="gr00t not available on this host")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{dataset_id}", response_model=DatasetResponse, dependencies=_auth)
async def get_dataset(dataset_id: str, store=Depends(get_store)) -> DatasetResponse:
    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetResponse(**dataset)


@router.delete("/{dataset_id}", status_code=204, dependencies=_auth)
async def delete_dataset(dataset_id: str, store=Depends(get_store)):
    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    store.delete_dataset(dataset_id)


# ── Inspect ──────────────────────────────────────────────────────────


@router.post("/inspect", response_model=InspectResponse, dependencies=_auth)
async def inspect_dataset(body: InspectRequest) -> InspectResponse:
    validate_path_param(body.dataset_path, must_exist=True)
    p = Path(body.dataset_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {body.dataset_path}")

    info_str = modality_str = tasks_str = stats_str = ""

    info_file = p / "meta" / "info.json"
    if info_file.exists():
        info_str = info_file.read_text()

    modality_file = p / "meta" / "modality.json"
    if modality_file.exists():
        modality_str = modality_file.read_text()

    tasks_file = p / "meta" / "tasks.jsonl"
    if tasks_file.exists():
        tasks_str = tasks_file.read_text()

    stats_file = p / "meta" / "stats.json"
    if stats_file.exists():
        try:
            stats_data = json.loads(stats_file.read_text())
            summary = {}
            for key in list(stats_data.keys())[:20]:
                val = stats_data[key]
                if isinstance(val, dict):
                    summary[key] = {k: type(v).__name__ for k, v in val.items()}
                else:
                    summary[key] = str(val)[:100]
            stats_str = json.dumps(summary, indent=2)
        except Exception:
            stats_str = stats_file.read_text()[:2000]

    return InspectResponse(info=info_str, modality=modality_str, tasks=tasks_str, stats=stats_str)


# ── Episode Data ─────────────────────────────────────────────────────


@router.post("/episode", response_model=EpisodeDataResponse, dependencies=_auth)
async def get_episode_data(body: EpisodeRequest) -> EpisodeDataResponse:
    validate_path_param(body.dataset_path, must_exist=True)
    p = Path(body.dataset_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Dataset path not found: {body.dataset_path}")

    ep_str = f"episode_{body.episode_index:06d}"

    # Find parquet file
    parquet_path = p / "data" / "chunk-000" / f"{ep_str}.parquet"
    if not parquet_path.exists():
        for chunk_dir in sorted((p / "data").glob("chunk-*")):
            candidate = chunk_dir / f"{ep_str}.parquet"
            if candidate.exists():
                parquet_path = candidate
                break
        else:
            raise HTTPException(status_code=404, detail=f"Parquet not found for episode {body.episode_index}")

    # Size limit
    max_bytes = 500 * 1024 * 1024
    if parquet_path.stat().st_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Parquet too large ({parquet_path.stat().st_size / 1e6:.0f} MB, limit 500 MB)",
        )

    try:
        import pandas as pd

        df = pd.read_parquet(parquet_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read parquet: {exc}")

    # Find video
    video_path = None
    videos_dir = p / "videos"
    if videos_dir.exists():
        for match in sorted(videos_dir.rglob(f"{ep_str}.mp4")):
            video_path = str(match)
            break

    # Extract state traces
    import numpy as np

    state_traces: list[TrajectoryTrace] = []
    state_cols = [c for c in df.columns if c.startswith("observation.state")]
    for col in state_cols:
        vals = df[col].tolist()
        if vals and isinstance(vals[0], (list, tuple)):
            arr = np.array(vals)
            for dim in range(arr.shape[1]):
                state_traces.append(TrajectoryTrace(name=f"{col}[{dim}]", y=arr[:, dim].tolist()))
        else:
            state_traces.append(TrajectoryTrace(name=col, y=[float(v) for v in vals]))

    # Extract action traces
    action_traces: list[TrajectoryTrace] = []
    action_cols = [c for c in df.columns if c.startswith("action")]
    for col in action_cols:
        vals = df[col].tolist()
        if vals and isinstance(vals[0], (list, tuple)):
            arr = np.array(vals)
            for dim in range(arr.shape[1]):
                action_traces.append(TrajectoryTrace(name=f"{col}[{dim}]", y=arr[:, dim].tolist()))
        else:
            action_traces.append(TrajectoryTrace(name=col, y=[float(v) for v in vals]))

    # Task description
    task_desc = ""
    tasks_file = p / "meta" / "tasks.jsonl"
    if tasks_file.exists():
        try:
            task_index = None
            if "task_index" in df.columns and len(df) > 0:
                task_index = int(df["task_index"].iloc[0])
            tasks = [json.loads(line) for line in tasks_file.open()]
            if task_index is not None and task_index < len(tasks):
                task_desc = tasks[task_index].get("task", str(tasks[task_index]))
            elif tasks:
                task_desc = tasks[0].get("task", str(tasks[0]))
        except Exception:
            logger.debug("Failed to read task description", exc_info=True)

    return EpisodeDataResponse(
        video_path=video_path,
        state_traces=state_traces,
        action_traces=action_traces,
        task_description=task_desc,
    )
