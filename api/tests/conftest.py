"""Shared fixtures for API tests."""

from __future__ import annotations

import os
import tempfile

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
    """TestClient with valid auth header."""
    return TestClient(_app, headers={"Authorization": f"Bearer {api_key}"})


@pytest.fixture()
def unauth_client(_app) -> TestClient:
    """TestClient without auth header."""
    return TestClient(_app)
