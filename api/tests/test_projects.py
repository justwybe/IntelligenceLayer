"""Tests for project CRUD endpoints."""


def test_list_projects_empty(client):
    """Initially there should be no projects."""
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert res.json()["projects"] == []


def test_create_project(client):
    """Should create a project and return it."""
    res = client.post(
        "/api/projects",
        json={
            "name": "TestBot",
            "embodiment_tag": "GR1",
            "base_model": "nvidia/GR00T-N1.6-3B",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "TestBot"
    assert data["embodiment_tag"] == "GR1"
    assert "id" in data


def test_get_project(client):
    """Should retrieve a project by ID with summary stats."""
    create_res = client.post(
        "/api/projects",
        json={"name": "GetTest", "embodiment_tag": "GR1"},
    )
    pid = create_res.json()["id"]

    res = client.get(f"/api/projects/{pid}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == pid
    assert data["name"] == "GetTest"
    assert data["dataset_count"] == 0
    assert data["model_count"] == 0
    assert data["run_count"] == 0


def test_get_project_not_found(client):
    """Should return 404 for non-existent project."""
    res = client.get("/api/projects/nonexistent")
    assert res.status_code == 404


def test_delete_project(client):
    """Should delete a project."""
    create_res = client.post(
        "/api/projects",
        json={"name": "ToDelete", "embodiment_tag": "GR1"},
    )
    pid = create_res.json()["id"]

    res = client.delete(f"/api/projects/{pid}")
    assert res.status_code == 204

    # Verify it's gone
    res = client.get(f"/api/projects/{pid}")
    assert res.status_code == 404


def test_delete_project_not_found(client):
    """Should return 404 when deleting non-existent project."""
    res = client.delete("/api/projects/nonexistent")
    assert res.status_code == 404


def test_list_after_create(client):
    """List should include created projects."""
    client.post(
        "/api/projects",
        json={"name": "Project1", "embodiment_tag": "GR1"},
    )
    client.post(
        "/api/projects",
        json={"name": "Project2", "embodiment_tag": "new_embodiment"},
    )

    res = client.get("/api/projects")
    assert res.status_code == 200
    projects = res.json()["projects"]
    names = {p["name"] for p in projects}
    assert "Project1" in names
    assert "Project2" in names
