"""Tests for the health endpoint."""


def test_health_returns_200(unauth_client):
    """Health endpoint should be accessible without auth."""
    res = unauth_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "gpu_available" in data
    assert "gpu_count" in data
    assert "db_ok" in data
    assert "uptime_seconds" in data


def test_health_db_ok(unauth_client):
    """Health should report db_ok=True with a valid store."""
    res = unauth_client.get("/api/health")
    assert res.json()["db_ok"] is True
