"""Tests for the runs router."""

from __future__ import annotations

import pytest


@pytest.fixture()
def project_id(client):
    """Create a project and return its ID."""
    resp = client.post(
        "/api/projects",
        json={"name": "Run Test Project", "embodiment_tag": "new_embodiment"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestRunsCRUD:
    def test_list_empty(self, client, project_id):
        resp = client.get(f"/api/runs?project_id={project_id}")
        assert resp.status_code == 200
        assert resp.json()["runs"] == []

    def test_list_with_run_type_filter(self, client, project_id):
        resp = client.get(f"/api/runs?project_id={project_id}&run_type=stats_computation")
        assert resp.status_code == 200
        assert resp.json()["runs"] == []

    def test_get_not_found(self, client):
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404

    def test_status_not_found(self, client):
        resp = client.get("/api/runs/nonexistent/status")
        assert resp.status_code == 404

    def test_stop_not_found(self, client):
        resp = client.post("/api/runs/nonexistent/stop")
        assert resp.status_code == 404


class TestAuth:
    def test_list_requires_auth(self, unauth_client):
        resp = unauth_client.get("/api/runs")
        assert resp.status_code == 401

    def test_create_requires_auth(self, unauth_client):
        resp = unauth_client.post(
            "/api/runs?project_id=x",
            json={"run_type": "stats_computation", "config": {}},
        )
        assert resp.status_code == 401
