"""Tests for the training constants and metrics endpoints."""

from __future__ import annotations

import pytest


class TestTrainingConstants:
    def test_get_constants(self, client):
        resp = client.get("/api/training/constants")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        assert "Quick Start" in data["presets"]
        assert data["presets"]["Quick Start"]["max_steps"] == 10000
        assert "embodiment_choices" in data
        assert "new_embodiment" in data["embodiment_choices"]
        assert "isaac_lab_envs" in data
        assert "rl_algorithms" in data
        assert "PPO" in data["rl_algorithms"]
        assert "optimizer_choices" in data
        assert "adamw_torch_fused" in data["optimizer_choices"]
        assert "lr_scheduler_choices" in data
        assert "deepspeed_stages" in data

    def test_constants_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/training/constants")
        assert resp.status_code == 401


@pytest.fixture()
def project_id(client):
    resp = client.post(
        "/api/projects",
        json={"name": "Training Test Project", "embodiment_tag": "new_embodiment"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestTrainingMetrics:
    def test_metrics_not_found(self, client):
        resp = client.get("/api/runs/nonexistent/metrics")
        assert resp.status_code == 404

    def test_metrics_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/runs/some-id/metrics")
        assert resp.status_code == 401


class TestTrainingRunType:
    def test_rl_training_not_available(self, client, project_id):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={"run_type": "rl_training", "config": {}},
        )
        assert resp.status_code == 400
        assert "not yet available" in resp.json()["detail"]

    def test_unknown_run_type(self, client, project_id):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={"run_type": "nonexistent", "config": {}},
        )
        assert resp.status_code == 400
