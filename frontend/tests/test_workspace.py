"""Tests for WorkspaceStore — SQLite-backed persistence layer."""

from __future__ import annotations

import json
import threading

from frontend.services.workspace import WorkspaceStore


class TestProjectCRUD:
    def test_create_and_get_project(self, store):
        pid = store.create_project("Robot1", "gr1", "nvidia/GR00T-N1.6-3B")
        assert len(pid) == 12
        proj = store.get_project(pid)
        assert proj is not None
        assert proj["name"] == "Robot1"
        assert proj["embodiment_tag"] == "gr1"
        assert proj["base_model"] == "nvidia/GR00T-N1.6-3B"

    def test_list_projects(self, store):
        store.create_project("A", "gr1")
        store.create_project("B", "unitree_g1")
        projects = store.list_projects()
        assert len(projects) == 2
        names = {p["name"] for p in projects}
        assert names == {"A", "B"}

    def test_get_nonexistent_project(self, store):
        assert store.get_project("nonexistent") is None

    def test_delete_project_cascades(self, store):
        pid = store.create_project("ToDelete", "gr1")
        did = store.register_dataset(pid, "ds1", "/data/ds1")
        rid = store.create_run(pid, "training", {"lr": 0.001})
        mid = store.register_model(pid, "model1", "/models/m1")
        store.save_evaluation(rid, mid, "benchmark", {"accuracy": 0.95})

        store.delete_project(pid)
        assert store.get_project(pid) is None
        assert store.get_dataset(did) is None
        assert store.get_run(rid) is None
        assert store.get_model(mid) is None
        assert store.list_evaluations(model_id=mid) == []


class TestDatasetCRUD:
    def test_register_and_list_datasets(self, store, project_id):
        did = store.register_dataset(project_id, "ds1", "/data/ds1", episode_count=100)
        assert len(did) == 12
        datasets = store.list_datasets(project_id=project_id)
        assert len(datasets) == 1
        assert datasets[0]["name"] == "ds1"
        assert datasets[0]["episode_count"] == 100

    def test_dataset_with_metadata(self, store, project_id):
        meta = {"format": "lerobot_v2", "cameras": ["left", "right"]}
        did = store.register_dataset(project_id, "ds2", "/data/ds2", metadata=meta)
        ds = store.get_dataset(did)
        assert ds is not None
        parsed_meta = json.loads(ds["metadata"])
        assert parsed_meta["format"] == "lerobot_v2"

    def test_list_datasets_no_project_filter(self, store):
        pid1 = store.create_project("P1", "gr1")
        pid2 = store.create_project("P2", "gr1")
        store.register_dataset(pid1, "ds1", "/a")
        store.register_dataset(pid2, "ds2", "/b")
        all_ds = store.list_datasets()
        assert len(all_ds) == 2


class TestRunCRUD:
    def test_create_and_get_run(self, store, project_id):
        config = {"lr": 0.001, "epochs": 10}
        rid = store.create_run(project_id, "training", config)
        run = store.get_run(rid)
        assert run is not None
        assert run["status"] == "pending"
        assert run["run_type"] == "training"
        parsed_config = json.loads(run["config"])
        assert parsed_config["lr"] == 0.001

    def test_update_run_status(self, store, project_id):
        rid = store.create_run(project_id, "training", {})
        store.update_run(rid, status="running", started_at="2025-01-01T00:00:00")
        run = store.get_run(rid)
        assert run["status"] == "running"
        assert run["started_at"] == "2025-01-01T00:00:00"

    def test_update_run_metrics(self, store, project_id):
        rid = store.create_run(project_id, "training", {})
        store.update_run(rid, metrics={"loss": 0.5, "step": 1000})
        run = store.get_run(rid)
        metrics = json.loads(run["metrics"])
        assert metrics["loss"] == 0.5

    def test_update_run_ignores_unknown_fields(self, store, project_id):
        rid = store.create_run(project_id, "training", {})
        store.update_run(rid, unknown_field="should_be_ignored", status="running")
        run = store.get_run(rid)
        assert run["status"] == "running"

    def test_list_runs_with_filters(self, store, project_id):
        store.create_run(project_id, "training", {})
        store.create_run(project_id, "evaluation", {})
        store.create_run(project_id, "training", {})

        all_runs = store.list_runs(project_id=project_id)
        assert len(all_runs) == 3

        training_runs = store.list_runs(project_id=project_id, run_type="training")
        assert len(training_runs) == 2

    def test_get_active_runs(self, store, project_id):
        rid1 = store.create_run(project_id, "training", {})
        store.create_run(project_id, "evaluation", {})
        store.update_run(rid1, status="running")

        active = store.get_active_runs()
        # rid1 is "running", rid2 is still "pending" — both are active
        assert len(active) == 2


class TestModelCRUD:
    def test_register_and_list_models(self, store, project_id):
        store.register_model(
            project_id, "model-v1", "/models/v1",
            embodiment_tag="gr1", step=5000,
        )
        models = store.list_models(project_id=project_id)
        assert len(models) == 1
        assert models[0]["name"] == "model-v1"
        assert models[0]["step"] == 5000

    def test_get_model(self, store, project_id):
        mid = store.register_model(project_id, "m1", "/models/m1")
        model = store.get_model(mid)
        assert model is not None
        assert model["name"] == "m1"


class TestEvaluations:
    def test_save_and_list_evaluations(self, store, project_id):
        rid = store.create_run(project_id, "benchmark", {})
        mid = store.register_model(project_id, "m1", "/m1")
        store.save_evaluation(rid, mid, "benchmark", {"e2e_ms": 15.3, "freq_hz": 65})

        evals = store.list_evaluations(model_id=mid)
        assert len(evals) == 1
        metrics = json.loads(evals[0]["metrics"])
        assert metrics["e2e_ms"] == 15.3

    def test_list_evaluations_by_run_id(self, store, project_id):
        rid = store.create_run(project_id, "benchmark", {})
        store.save_evaluation(rid, "", "benchmark", {"metric": 1})
        store.save_evaluation(rid, "", "benchmark", {"metric": 2})

        evals = store.list_evaluations(run_id=rid)
        assert len(evals) == 2

    def test_save_evaluation_null_model_id(self, store, project_id):
        rid = store.create_run(project_id, "benchmark", {})
        store.save_evaluation(rid, "", "benchmark", {"e2e": 10})
        evals = store.list_evaluations(run_id=rid)
        assert len(evals) == 1
        # Empty string should be stored as NULL
        assert evals[0]["model_id"] is None


class TestActivityLog:
    def test_log_activity_on_create(self, store, project_id):
        # create_project already logs activity
        activity = store.recent_activity(project_id=project_id)
        assert len(activity) >= 1
        assert activity[0]["event_type"] == "project_created"

    def test_manual_log_activity(self, store, project_id):
        store.log_activity(project_id, "custom_event", "test", "123", "Test message")
        activity = store.recent_activity(project_id=project_id)
        custom = [a for a in activity if a["event_type"] == "custom_event"]
        assert len(custom) == 1

    def test_recent_activity_limit(self, store, project_id):
        for i in range(10):
            store.log_activity(project_id, f"event_{i}")
        activity = store.recent_activity(project_id=project_id, limit=5)
        # +1 for project_created
        assert len(activity) == 5


class TestTransactions:
    def test_create_project_is_atomic(self, store):
        """Both INSERT (project + activity_log) happen in one transaction."""
        pid = store.create_project("Atomic", "gr1")
        proj = store.get_project(pid)
        activity = store.recent_activity(project_id=pid)
        assert proj is not None
        assert len(activity) >= 1

    def test_delete_project_is_atomic(self, store):
        """All cascading deletes happen in one transaction."""
        pid = store.create_project("ToCascade", "gr1")
        store.register_dataset(pid, "ds", "/ds")
        store.create_run(pid, "training", {})
        store.register_model(pid, "m", "/m")
        store.delete_project(pid)
        # Everything should be cleaned up
        assert store.list_datasets(project_id=pid) == []
        assert store.list_runs(project_id=pid) == []
        assert store.list_models(project_id=pid) == []


class TestSchemaMigration:
    def test_migrate_creates_version_table(self, db_path):
        store = WorkspaceStore(db_path=db_path)
        conn = store._conn
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] >= 1
        store.close()

    def test_migrate_creates_indexes(self, db_path):
        store = WorkspaceStore(db_path=db_path)
        conn = store._conn
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        index_names = {r[0] for r in indexes}
        assert "idx_runs_project" in index_names
        assert "idx_runs_status" in index_names
        store.close()

    def test_reopen_database_is_idempotent(self, db_path):
        s1 = WorkspaceStore(db_path=db_path)
        pid = s1.create_project("Persist", "gr1")
        s1.close()

        s2 = WorkspaceStore(db_path=db_path)
        proj = s2.get_project(pid)
        assert proj is not None
        assert proj["name"] == "Persist"
        s2.close()


class TestConnectionManagement:
    def test_close_and_reopen(self, db_path):
        store = WorkspaceStore(db_path=db_path)
        pid = store.create_project("X", "gr1")
        store.close()
        # After close, accessing _conn should create a new connection
        proj = store.get_project(pid)
        assert proj is not None
        store.close()

    def test_thread_safety(self, db_path):
        store = WorkspaceStore(db_path=db_path)
        errors = []

        def worker(n):
            try:
                pid = store.create_project(f"Thread{n}", "gr1")
                proj = store.get_project(pid)
                if proj is None:
                    errors.append(f"Thread{n}: project not found after create")
            except Exception as e:
                errors.append(f"Thread{n}: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread safety errors: {errors}"
        assert len(store.list_projects()) == 5
        store.close()
