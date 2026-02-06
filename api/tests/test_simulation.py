"""Tests for simulation constants, eval metrics, and compare endpoints."""

from __future__ import annotations

import pytest


class TestSimulationConstants:
    def test_get_constants(self, client):
        resp = client.get("/api/simulation/constants")
        assert resp.status_code == 200
        data = resp.json()
        assert "sim_tasks" in data
        assert "LIBERO" in data["sim_tasks"]
        assert len(data["sim_tasks"]["LIBERO"]) > 0
        assert "SimplerEnv" in data["sim_tasks"]
        assert "BEHAVIOR" in data["sim_tasks"]
        assert "embodiment_choices" in data
        assert "new_embodiment" in data["embodiment_choices"]

    def test_constants_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/simulation/constants")
        assert resp.status_code == 401


@pytest.fixture()
def project_id(client):
    resp = client.post(
        "/api/projects",
        json={"name": "Sim Test Project", "embodiment_tag": "new_embodiment"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestEvalMetrics:
    def test_eval_metrics_not_found(self, client):
        resp = client.get("/api/runs/nonexistent/eval-metrics")
        assert resp.status_code == 404

    def test_eval_metrics_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/runs/some-id/eval-metrics")
        assert resp.status_code == 401


class TestArtifacts:
    def test_artifacts_not_found(self, client):
        resp = client.get("/api/runs/nonexistent/artifacts")
        assert resp.status_code == 404

    def test_artifact_file_not_found(self, client):
        resp = client.get("/api/runs/nonexistent/artifacts/test.png")
        assert resp.status_code == 404

    def test_artifacts_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/runs/some-id/artifacts")
        assert resp.status_code == 401

    def test_artifact_path_traversal(self, client, project_id):
        # Create a run to test against
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={"run_type": "simulation", "config": {"task": "test", "model_path": "test"}},
        )
        # The run will fail (no real process), but we can test the artifact endpoint
        # with path traversal attempt — FastAPI normalizes the path so ".." is resolved,
        # but the file won't be found (400 or 404 both indicate blocked traversal)
        if resp.status_code == 201:
            run_id = resp.json()["id"]
            resp = client.get(f"/api/runs/{run_id}/artifacts/../../../etc/passwd")
            assert resp.status_code in (400, 404)


class TestSimulationRunType:
    def test_simulation_run_type(self, client, project_id):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "simulation",
                "config": {
                    "task": "libero/libero_panda/KITCHEN_SCENE1_open_the_bottom_drawer_of_the_cabinet",
                    "model_path": "/tmp/test_model",
                    "max_steps": 504,
                    "n_action_steps": 8,
                    "n_episodes": 10,
                    "n_envs": 1,
                },
            },
        )
        # Should create the run (201) — the actual process may fail but the run record is created
        assert resp.status_code == 201
        data = resp.json()
        assert data["run_type"] == "simulation"

    def test_evaluation_run_type(self, client, project_id):
        resp = client.post(
            f"/api/runs?project_id={project_id}",
            json={
                "run_type": "evaluation",
                "config": {
                    "dataset_path": "demo_data/cube_to_bowl_5/",
                    "model_path": "/tmp/test_model",
                    "embodiment_tag": "new_embodiment",
                    "traj_ids": "0",
                    "steps": 200,
                    "action_horizon": 16,
                },
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["run_type"] == "evaluation"


class TestEvaluations:
    def test_list_evaluations_empty(self, client):
        resp = client.get("/api/evaluations")
        assert resp.status_code == 200
        assert resp.json()["evaluations"] == []

    def test_compare_empty(self, client):
        resp = client.get("/api/evaluations/compare")
        assert resp.status_code == 200
        assert resp.json()["entries"] == []

    def test_evaluations_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/evaluations")
        assert resp.status_code == 401

    def test_compare_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/evaluations/compare")
        assert resp.status_code == 401


class TestEvalMetricsParsing:
    """Unit tests for _parse_eval_metrics."""

    def test_parse_success_rate(self):
        from api.routers.runs import _parse_eval_metrics

        log = "Episode results: success rate: 0.85\nDone."
        result = _parse_eval_metrics(log)
        assert len(result.sim_metrics) == 1
        assert result.sim_metrics[0].name == "Success Rate"
        assert result.sim_metrics[0].value == "0.85"

    def test_parse_timing(self):
        from api.routers.runs import _parse_eval_metrics

        log = "Collecting 10 episodes took 42.5 seconds"
        result = _parse_eval_metrics(log)
        assert any(m.name == "Total Time (s)" for m in result.sim_metrics)

    def test_parse_mse_mae(self):
        from api.routers.runs import _parse_eval_metrics

        log = (
            "MSE for trajectory 0: 1.23e-03, MAE: 4.56e-02\n"
            "MSE for trajectory 1: 2.34e-03, MAE: 5.67e-02\n"
        )
        result = _parse_eval_metrics(log)
        assert len(result.eval_metrics) == 2
        assert result.eval_metrics[0].trajectory == 0
        assert result.eval_metrics[0].mse == pytest.approx(1.23e-03)
        assert result.eval_metrics[0].mae == pytest.approx(4.56e-02)
        assert result.eval_metrics[1].trajectory == 1

    def test_parse_empty_log(self):
        from api.routers.runs import _parse_eval_metrics

        result = _parse_eval_metrics("")
        assert result.sim_metrics == []
        assert result.eval_metrics == []
