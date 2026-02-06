"""Tests for authentication middleware."""


def test_valid_key_returns_200(client):
    """Authenticated request should succeed."""
    res = client.get("/api/projects")
    assert res.status_code == 200


def test_missing_key_returns_401(unauth_client):
    """Request without auth header should be rejected."""
    res = unauth_client.get("/api/projects")
    assert res.status_code == 401


def test_invalid_key_returns_401(unauth_client):
    """Request with wrong key should be rejected."""
    res = unauth_client.get(
        "/api/projects",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert res.status_code == 401


def test_health_no_auth_required(unauth_client):
    """Health endpoint should not require authentication."""
    res = unauth_client.get("/api/health")
    assert res.status_code == 200
