"""Tests for path validation in API endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture()
def project_id(client):
    """Create a project and return its ID."""
    resp = client.post(
        "/api/projects",
        json={"name": "Path Test Project", "embodiment_tag": "new_embodiment"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestPathValidation:
    """Ensure path validation rejects paths outside allowed roots."""

    def test_create_dataset_rejects_traversal(self, client, project_id):
        resp = client.post(
            f"/api/datasets?project_id={project_id}",
            json={"name": "evil", "path": "/etc/passwd"},
        )
        assert resp.status_code == 400
        assert "outside allowed directories" in resp.json()["detail"]

    def test_create_dataset_rejects_dotdot(self, client, project_id):
        resp = client.post(
            f"/api/datasets?project_id={project_id}",
            json={"name": "evil", "path": "../../../etc/shadow"},
        )
        assert resp.status_code == 400

    def test_inspect_rejects_outside_path(self, client):
        resp = client.post(
            "/api/datasets/inspect",
            json={"dataset_path": "/etc/hosts"},
        )
        assert resp.status_code == 400

    def test_episode_rejects_outside_path(self, client):
        resp = client.post(
            "/api/datasets/episode",
            json={"dataset_path": "/etc/passwd", "episode_index": 0},
        )
        assert resp.status_code == 400

    def test_create_dataset_allows_valid_path(self, client, project_id):
        """Paths under home dir should be allowed."""
        import os
        import tempfile
        from pathlib import Path

        home = os.path.expanduser("~")
        ds_dir = tempfile.mkdtemp(dir=home, prefix=".wybe_test_")
        try:
            resp = client.post(
                f"/api/datasets?project_id={project_id}",
                json={"name": "valid", "path": ds_dir},
            )
            assert resp.status_code == 201
        finally:
            Path(ds_dir).rmdir()

    def test_run_create_rejects_outside_paths(self, client, project_id):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "stats_computation",
                "config": {
                    "dataset_path": "/etc/shadow",
                    "embodiment_tag": "new_embodiment",
                },
            },
        )
        assert resp.status_code == 400

    def test_video_rejects_outside_path(self, client, api_key):
        resp = client.get(
            f"/api/datasets/video?path=/etc/passwd&token={api_key}",
        )
        assert resp.status_code == 400
