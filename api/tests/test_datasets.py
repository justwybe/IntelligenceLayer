"""Tests for the datasets router."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def project_id(client):
    """Create a project and return its ID."""
    resp = client.post(
        "/api/projects",
        json={"name": "Test Project", "embodiment_tag": "new_embodiment"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestDatasetsCRUD:
    def test_list_empty(self, client, project_id):
        resp = client.get(f"/api/datasets?project_id={project_id}")
        assert resp.status_code == 200
        assert resp.json()["datasets"] == []

    def test_create_and_get(self, client, project_id, tmp_path):
        ds_path = str(tmp_path / "my_dataset")
        Path(ds_path).mkdir()

        resp = client.post(
            f"/api/datasets?project_id={project_id}",
            json={"name": "test_ds", "path": ds_path, "source": "imported"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test_ds"
        assert data["path"] == ds_path
        assert data["source"] == "imported"
        ds_id = data["id"]

        # Get by ID
        resp = client.get(f"/api/datasets/{ds_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "test_ds"

    def test_create_with_episodes(self, client, project_id, tmp_path):
        ds_path = tmp_path / "ds_with_eps"
        meta = ds_path / "meta"
        meta.mkdir(parents=True)
        (meta / "episodes.jsonl").write_text('{"index":0}\n{"index":1}\n{"index":2}\n')

        resp = client.post(
            f"/api/datasets?project_id={project_id}",
            json={"name": "eps_ds", "path": str(ds_path)},
        )
        assert resp.status_code == 201
        assert resp.json()["episode_count"] == 3

    def test_list_with_data(self, client, project_id, tmp_path):
        ds_path = str(tmp_path / "ds1")
        Path(ds_path).mkdir()
        client.post(
            f"/api/datasets?project_id={project_id}",
            json={"name": "ds1", "path": ds_path},
        )
        resp = client.get(f"/api/datasets?project_id={project_id}")
        assert resp.status_code == 200
        assert len(resp.json()["datasets"]) == 1

    def test_delete(self, client, project_id, tmp_path):
        ds_path = str(tmp_path / "del_ds")
        Path(ds_path).mkdir()
        resp = client.post(
            f"/api/datasets?project_id={project_id}",
            json={"name": "del_me", "path": ds_path},
        )
        ds_id = resp.json()["id"]

        resp = client.delete(f"/api/datasets/{ds_id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/datasets/{ds_id}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/datasets/nonexistent")
        assert resp.status_code == 404

    def test_get_not_found(self, client):
        resp = client.get("/api/datasets/nonexistent")
        assert resp.status_code == 404


class TestConstants:
    def test_get_constants(self, client):
        resp = client.get("/api/datasets/constants")
        assert resp.status_code == 200
        data = resp.json()
        assert "embodiment_choices" in data
        assert "mimic_envs" in data
        assert "source_options" in data
        assert len(data["embodiment_choices"]) > 0
        assert "imported" in data["source_options"]


class TestInspect:
    def test_inspect_nonexistent_path(self, client):
        resp = client.post(
            "/api/datasets/inspect",
            json={"dataset_path": "/nonexistent/path"},
        )
        # Path validation rejects paths outside allowed roots before checking existence
        assert resp.status_code == 400

    def test_inspect_empty_dataset(self, client, tmp_path):
        ds_path = str(tmp_path / "empty_ds")
        Path(ds_path).mkdir()

        resp = client.post(
            "/api/datasets/inspect",
            json={"dataset_path": ds_path},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"] == ""
        assert data["modality"] == ""
        assert data["tasks"] == ""
        assert data["stats"] == ""

    def test_inspect_with_meta_files(self, client, tmp_path):
        ds_path = tmp_path / "meta_ds"
        meta = ds_path / "meta"
        meta.mkdir(parents=True)
        (meta / "info.json").write_text('{"format":"lerobot_v2"}')
        (meta / "tasks.jsonl").write_text('{"task":"pick up cube"}\n')

        resp = client.post(
            "/api/datasets/inspect",
            json={"dataset_path": str(ds_path)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "lerobot_v2" in data["info"]
        assert "pick up cube" in data["tasks"]


class TestAuth:
    def test_list_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/datasets")
        assert resp.status_code == 401

    def test_constants_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/datasets/constants")
        assert resp.status_code == 401
