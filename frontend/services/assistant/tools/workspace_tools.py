"""Workspace tools — projects, datasets, models, runs."""

from __future__ import annotations

from frontend.constants import EMBODIMENT_CHOICES
from frontend.services.assistant.tools.base import ToolContext, ToolDef, ToolResult, json_output


def _list_projects(ctx: ToolContext, args: dict) -> ToolResult:
    projects = ctx.store.list_projects()
    if not projects:
        return ToolResult(output="No projects found. Create one first.")
    rows = []
    for p in projects:
        rows.append({
            "id": p["id"],
            "name": p["name"],
            "embodiment": p["embodiment_tag"],
            "base_model": p["base_model"],
            "created": p.get("created_at", ""),
        })
    return ToolResult(output=json_output(rows))


def _create_project(ctx: ToolContext, args: dict) -> ToolResult:
    name = args.get("name", "").strip()
    if not name:
        return ToolResult(output="Project name is required.", is_error=True)
    embodiment = args.get("embodiment_tag", "new_embodiment")
    base_model = args.get("base_model", "nvidia/GR00T-N1.6-3B")
    pid = ctx.store.create_project(name, embodiment, base_model)
    return ToolResult(output=f"Project created successfully.\nID: {pid}\nName: {name}\nEmbodiment: {embodiment}")


def _get_project_summary(ctx: ToolContext, args: dict) -> ToolResult:
    pid = args.get("project_id") or ctx.current_project_id
    if not pid:
        return ToolResult(output="No project selected. Please select or specify a project_id.", is_error=True)
    proj = ctx.store.get_project(pid)
    if not proj:
        return ToolResult(output=f"Project {pid} not found.", is_error=True)

    datasets = ctx.store.list_datasets(project_id=pid)
    models = ctx.store.list_models(project_id=pid)
    runs = ctx.store.list_runs(project_id=pid)
    active_runs = [r for r in runs if r["status"] in ("running", "pending")]

    summary = {
        "project": {
            "id": proj["id"],
            "name": proj["name"],
            "embodiment": proj["embodiment_tag"],
            "base_model": proj["base_model"],
        },
        "counts": {
            "datasets": len(datasets),
            "models": len(models),
            "total_runs": len(runs),
            "active_runs": len(active_runs),
        },
        "datasets": [{"name": d["name"], "path": d["path"], "episodes": d.get("episode_count")} for d in datasets[:10]],
        "models": [{"name": m["name"], "path": m["path"], "step": m.get("step")} for m in models[:10]],
    }
    return ToolResult(output=json_output(summary))


def _list_datasets(ctx: ToolContext, args: dict) -> ToolResult:
    pid = args.get("project_id") or ctx.current_project_id
    datasets = ctx.store.list_datasets(project_id=pid)
    if not datasets:
        return ToolResult(output="No datasets registered.")
    rows = []
    for d in datasets:
        rows.append({
            "id": d["id"],
            "name": d["name"],
            "path": d["path"],
            "episodes": d.get("episode_count"),
            "source": d.get("source", "imported"),
        })
    return ToolResult(output=json_output(rows))


def _list_models(ctx: ToolContext, args: dict) -> ToolResult:
    pid = args.get("project_id") or ctx.current_project_id
    models = ctx.store.list_models(project_id=pid)
    if not models:
        return ToolResult(output="No models registered.")
    rows = []
    for m in models:
        rows.append({
            "id": m["id"],
            "name": m["name"],
            "path": m["path"],
            "step": m.get("step"),
            "embodiment": m.get("embodiment_tag"),
        })
    return ToolResult(output=json_output(rows))


def _list_runs(ctx: ToolContext, args: dict) -> ToolResult:
    pid = args.get("project_id") or ctx.current_project_id
    run_type = args.get("run_type")
    runs = ctx.store.list_runs(project_id=pid, run_type=run_type)
    if not runs:
        return ToolResult(output="No runs found.")
    rows = []
    for r in runs[:20]:
        rows.append({
            "id": r["id"],
            "type": r["run_type"],
            "status": r["status"],
            "started": r.get("started_at", ""),
        })
    return ToolResult(output=json_output(rows))


WORKSPACE_TOOLS = [
    ToolDef(
        name="list_projects",
        description="List all projects in the workspace.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_list_projects,
        category="workspace",
    ),
    ToolDef(
        name="create_project",
        description="Create a new project.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "embodiment_tag": {
                    "type": "string",
                    "description": "Robot embodiment tag",
                    "enum": EMBODIMENT_CHOICES,
                },
                "base_model": {
                    "type": "string",
                    "description": "Base model path",
                    "default": "nvidia/GR00T-N1.6-3B",
                },
            },
            "required": ["name"],
        },
        handler=_create_project,
        category="workspace",
    ),
    ToolDef(
        name="get_project_summary",
        description="Get a summary of the current project including datasets, models, and runs.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (optional, uses current project if not specified)"},
            },
            "required": [],
        },
        handler=_get_project_summary,
        category="workspace",
    ),
    ToolDef(
        name="list_datasets",
        description="List all datasets in the current project.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (optional)"},
            },
            "required": [],
        },
        handler=_list_datasets,
        category="workspace",
    ),
    ToolDef(
        name="list_models",
        description="List all registered models in the current project.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (optional)"},
            },
            "required": [],
        },
        handler=_list_models,
        category="workspace",
    ),
    ToolDef(
        name="list_runs",
        description="List training, evaluation, and other runs for the current project.",
        parameters={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID (optional)"},
                "run_type": {"type": "string", "description": "Filter by run type (training, evaluation, simulation, benchmark, etc.)"},
            },
            "required": [],
        },
        handler=_list_runs,
        category="workspace",
    ),
]
