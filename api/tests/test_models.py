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


class TestModelsConstants:
    def test_get_constants(self, client):
        resp = client.get("/api/models/constants")
        assert resp.status_code == 200
        data = resp.json()
        assert "embodiment_choices" in data
        assert isinstance(data["embodiment_choices"], list)
        assert "new_embodiment" in data["embodiment_choices"]

    def test_constants_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/models/constants")
        assert resp.status_code == 401


class TestServerDeployStop:
    def test_deploy(self, client):
        resp = client.post(
            "/api/server/deploy",
            json={
                "model_path": "/test/model",
                "embodiment_tag": "new_embodiment",
                "port": 5555,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "status" in data

    def test_stop(self, client):
        resp = client.post("/api/server/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "status" in data

    def test_deploy_requires_auth(self, unauth_client):
        resp = unauth_client.post(
            "/api/server/deploy",
            json={"model_path": "/test", "embodiment_tag": "new_embodiment"},
        )
        assert resp.status_code == 401

    def test_stop_requires_auth(self, unauth_client):
        resp = unauth_client.post("/api/server/stop")
        assert resp.status_code == 401


class TestRunTypes:
    def test_create_onnx_export_run(self, client, project_id, tmp_path):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "onnx_export",
                "config": {
                    "model_path": str(tmp_path / "model"),
                    "dataset_path": str(tmp_path / "dataset"),
                    "embodiment_tag": "new_embodiment",
                    "output_dir": str(tmp_path / "output"),
                },
            },
        )
        assert resp.status_code == 201
        assert resp.json()["run_type"] == "onnx_export"

    def test_create_tensorrt_build_run(self, client, project_id, tmp_path):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "tensorrt_build",
                "config": {
                    "onnx_path": str(tmp_path / "model.onnx"),
                    "engine_path": str(tmp_path / "model.bf16.trt"),
                    "precision": "bf16",
                },
            },
        )
        assert resp.status_code == 201
        assert resp.json()["run_type"] == "tensorrt_build"

    def test_create_benchmark_run(self, client, project_id, tmp_path):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "benchmark",
                "config": {
                    "model_path": str(tmp_path / "model"),
                    "embodiment_tag": "new_embodiment",
                    "num_iterations": 50,
                },
            },
        )
        assert resp.status_code == 201
        assert resp.json()["run_type"] == "benchmark"


class TestBenchmarkMetrics:
    def test_benchmark_metrics_not_found(self, client):
        resp = client.get("/api/runs/nonexistent/benchmark-metrics")
        assert resp.status_code == 404

    def test_benchmark_metrics_empty(self, client, project_id, tmp_path):
        # Create a benchmark run
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "benchmark",
                "config": {"model_path": str(tmp_path / "model"), "embodiment_tag": "new_embodiment"},
            },
        )
        run_id = resp.json()["id"]
        resp2 = client.get(f"/api/runs/{run_id}/benchmark-metrics")
        assert resp2.status_code == 200
        data = resp2.json()
        assert "rows" in data
        assert "status" in data


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
