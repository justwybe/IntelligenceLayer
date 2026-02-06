"""FastAPI application factory for Wybe Studio API.

Launch:
    cd /root/IntelligenceLayer
    .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is on sys.path so gr00t/frontend imports work
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from api.config import settings
from api.routers import activity, chat, datasets, evaluations, gpu, health, models, projects, runs, server, simulation, training
from api.ws.gpu import gpu_manager, router as gpu_ws_router

logger = logging.getLogger(__name__)


async def _gpu_broadcast_loop():
    """Background task: broadcast GPU stats to WebSocket clients."""
    from frontend.services.gpu_monitor import get_gpu_info

    while True:
        await asyncio.sleep(settings.gpu_broadcast_interval)
        if gpu_manager.active_count == 0:
            continue
        try:
            gpus = get_gpu_info()
            await gpu_manager.broadcast_json({"gpus": gpus})
        except Exception:
            logger.exception("GPU broadcast error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared services on startup, clean up on shutdown."""
    from frontend.services.path_utils import init_allowed_roots
    from frontend.services.process_manager import ProcessManager
    from frontend.services.server_manager import ServerManager
    from frontend.services.task_runner import TaskRunner
    from frontend.services.workspace import WorkspaceStore

    if settings.wybe_api_key:
        logger.info("Auth enabled — API key required")
    else:
        logger.info("Auth disabled — open access")

    # Path validation
    init_allowed_roots(PROJECT_ROOT)

    # Core services (mirrors frontend/app.py:57-72)
    store = WorkspaceStore(db_path=settings.db_path)
    process_manager = ProcessManager()
    server_manager = ServerManager(process_manager, project_root=PROJECT_ROOT)
    task_runner = TaskRunner(store)
    task_runner.reconnect_on_startup()

    # AI Agent (lazy — only if anthropic key is available)
    agent = None
    try:
        from frontend.services.assistant.agent import WybeAgent

        agent = WybeAgent(
            store=store,
            task_runner=task_runner,
            server_manager=server_manager,
            project_root=PROJECT_ROOT,
        )
    except Exception:
        logger.warning("WybeAgent unavailable (missing anthropic key?)")

    # Attach to app state for dependency injection
    app.state.store = store
    app.state.process_manager = process_manager
    app.state.server_manager = server_manager
    app.state.task_runner = task_runner
    app.state.agent = agent
    app.state.project_root = PROJECT_ROOT
    app.state.start_time = time.time()

    # Start GPU broadcast background task
    broadcast_task = asyncio.create_task(_gpu_broadcast_loop())

    logger.info("Wybe Studio API started")
    yield

    # Shutdown
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    store.close()
    logger.info("Wybe Studio API stopped")


app = FastAPI(
    title="Wybe Studio API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(projects.router)
app.include_router(gpu.router)
app.include_router(activity.router)
app.include_router(server.router)
app.include_router(datasets.router)
app.include_router(runs.router)
app.include_router(training.router)
app.include_router(models.router)
app.include_router(simulation.router)
app.include_router(evaluations.router)

# WebSocket router
app.include_router(gpu_ws_router)
