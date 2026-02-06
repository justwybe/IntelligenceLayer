"""Tests for the GPU endpoint."""


def test_gpu_returns_structured_data(client):
    """GPU endpoint should return structured response."""
    res = client.get("/api/gpu")
    assert res.status_code == 200
    data = res.json()
    assert "gpus" in data
    assert "gpu_available" in data
    assert "gpu_count" in data
    assert isinstance(data["gpus"], list)
    assert data["gpu_count"] == len(data["gpus"])


def test_gpu_requires_auth(unauth_client):
    """GPU endpoint should require authentication."""
    res = unauth_client.get("/api/gpu")
    assert res.status_code == 401
