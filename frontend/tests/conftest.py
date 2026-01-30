"""Shared fixtures for frontend tests."""

from __future__ import annotations

import pytest

from frontend.services.workspace import WorkspaceStore


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def db_path(tmp_path):
    """Provide a temporary database path."""
    return str(tmp_path / "test_studio.db")


@pytest.fixture
def store(db_path):
    """Provide a WorkspaceStore backed by a temporary database."""
    s = WorkspaceStore(db_path=db_path)
    yield s
    s.close()


@pytest.fixture
def project_id(store):
    """Create and return a test project ID."""
    return store.create_project(
        name="TestProject",
        embodiment_tag="new_embodiment",
        base_model="nvidia/GR00T-N1.6-3B",
    )
