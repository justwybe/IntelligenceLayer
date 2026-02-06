"""Tests for the models router."""

from __future__ import annotations

import pytest


@pytest.fixture()
def project_id(client):
    resp = client.post(
        "/api/projects",
        json={"name": "Model Test Project", "embodiment_tag": "new_embodiment"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestModelsCRUD:
    def test_list_empty(self, client, project_id):
        resp = client.get(f"/api/models?project_id={project_id}")
        assert resp.status_code == 200
        assert resp.json()["models"] == []

    def test_register_and_get(self, client, project_id):
        resp = client.post(
            f"/api/models?project_id={project_id}",
            json={
                "name": "test-model-v1",
                "path": "/outputs/checkpoint-5000",
                "base_model": "nvidia/GR00T-N1.6-3B",
                "embodiment_tag": "new_embodiment",
                "step": 5000,
            },
        )
        assert resp.status_code == 201
        model = resp.json()
        assert model["name"] == "test-model-v1"
        assert model["path"] == "/outputs/checkpoint-5000"
        assert model["step"] == 5000

        # Get by ID
        resp2 = client.get(f"/api/models/{model['id']}")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == model["id"]

    def test_list_after_register(self, client, project_id):
        client.post(
            f"/api/models?project_id={project_id}",
            json={"name": "model-a", "path": "/a"},
        )
        client.post(
            f"/api/models?project_id={project_id}",
            json={"name": "model-b", "path": "/b"},
        )
        resp = client.get(f"/api/models?project_id={project_id}")
        assert resp.status_code == 200
        assert len(resp.json()["models"]) == 2

    def test_get_not_found(self, client):
        resp = client.get("/api/models/nonexistent")
        assert resp.status_code == 404

    def test_register_project_not_found(self, client):
        resp = client.post(
            "/api/models?project_id=nonexistent",
            json={"name": "m", "path": "/p"},
        )
        assert resp.status_code == 404


class TestAuth:
    def test_list_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/models")
        assert resp.status_code == 401

    def test_register_requires_auth(self, unauth_client):
        resp = unauth_client.post(
            "/api/models?project_id=x",
            json={"name": "m", "path": "/p"},
        )
        assert resp.status_code == 401
