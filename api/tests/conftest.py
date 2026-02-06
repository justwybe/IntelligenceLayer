"""Shared fixtures for API tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api_key() -> str:
    return "test-key-12345"


@pytest.fixture()
def _app(tmp_path, api_key):
    """Create a test FastAPI app with an in-memory store."""
    db_path = str(tmp_path / "test.db")

    # Patch settings before importing main
    os.environ["WYBE_API_KEY"] = api_key
    os.environ["DB_PATH"] = db_path

    from api.config import settings

    settings.wybe_api_key = api_key
    settings.db_path = db_path

    from api.main import app

    return app


@pytest.fixture()
def client(_app, api_key) -> TestClient:
    """TestClient with valid auth header, lifespan started."""
    import tempfile
    from pathlib import Path

    with TestClient(_app, headers={"Authorization": f"Bearer {api_key}"}) as c:
        # Add system temp dir to allowed roots so test paths pass validation
        import frontend.services.path_utils as pu
        temp_root = str(Path(tempfile.gettempdir()).resolve())
        if temp_root not in pu._allowed_roots:
            pu._allowed_roots.append(temp_root)
        # macOS /var -> /private/var symlink
        private_temp = str(Path("/private/tmp").resolve())
        if private_temp not in pu._allowed_roots:
            pu._allowed_roots.append(private_temp)
        yield c


@pytest.fixture()
def unauth_client(_app) -> TestClient:
    """TestClient without auth header, lifespan started."""
    with TestClient(_app) as c:
        yield c
