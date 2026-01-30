"""Tests for TaskRunner — subprocess manager with DB-backed state."""

from __future__ import annotations

import sys
import time

import pytest

from frontend.services.task_runner import TaskRunner


@pytest.fixture
def runner(store, tmp_path):
    """Provide a TaskRunner with a temp log directory."""
    return TaskRunner(store, log_dir=str(tmp_path / "logs"))


@pytest.fixture
def run_id(store, project_id):
    """Create a pending run record and return its ID."""
    return store.create_run(project_id, "test_run", {"test": True})


class TestLaunch:
    def test_launch_simple_command(self, runner, store, run_id):
        msg = runner.launch(run_id, [sys.executable, "-c", "print('hello')"])
        assert "launched" in msg
        # Wait for process to exit
        time.sleep(1)
        run = store.get_run(run_id)
        assert run["status"] == "completed"

    def test_launch_failing_command(self, runner, store, run_id):
        msg = runner.launch(run_id, [sys.executable, "-c", "import sys; sys.exit(1)"])
        assert "launched" in msg
        time.sleep(1)
        run = store.get_run(run_id)
        assert run["status"] == "failed"

    def test_launch_duplicate_prevented(self, runner, store, run_id):
        msg1 = runner.launch(run_id, [sys.executable, "-c", "import time; time.sleep(5)"])
        assert "launched" in msg1
        msg2 = runner.launch(run_id, [sys.executable, "-c", "print('dup')"])
        assert "already running" in msg2
        runner.stop(run_id)

    def test_launch_invalid_command(self, runner, store, run_id):
        msg = runner.launch(run_id, ["/nonexistent/binary"])
        assert "Failed to launch" in msg
        run = store.get_run(run_id)
        assert run["status"] == "failed"

    def test_launch_sets_pid(self, runner, store, run_id):
        runner.launch(run_id, [sys.executable, "-c", "import time; time.sleep(5)"])
        run = store.get_run(run_id)
        assert run["pid"] is not None
        assert run["pid"] > 0
        runner.stop(run_id)


class TestStop:
    def test_stop_running_process(self, runner, store, run_id):
        runner.launch(run_id, [sys.executable, "-c", "import time; time.sleep(30)"])
        time.sleep(0.3)
        msg = runner.stop(run_id)
        assert "stopped" in msg
        run = store.get_run(run_id)
        assert run["status"] == "stopped"

    def test_stop_unknown_run(self, runner):
        msg = runner.stop("nonexistent")
        assert "not found" in msg

    def test_stop_already_exited(self, runner, store, run_id):
        runner.launch(run_id, [sys.executable, "-c", "print('done')"])
        time.sleep(1)
        msg = runner.stop(run_id)
        # Process already finished — _wait_for_exit already removed it
        assert "not found" in msg or "already exited" in msg


class TestStatus:
    def test_status_running(self, runner, run_id):
        runner.launch(run_id, [sys.executable, "-c", "import time; time.sleep(5)"])
        assert runner.status(run_id) == "running"
        runner.stop(run_id)

    def test_status_completed(self, runner, store, run_id):
        runner.launch(run_id, [sys.executable, "-c", "print('ok')"])
        time.sleep(1)
        assert runner.status(run_id) == "completed"

    def test_status_not_found(self, runner):
        assert runner.status("nonexistent") == "not found"


class TestLogs:
    def test_tail_log_captures_output(self, runner, run_id):
        runner.launch(run_id, [sys.executable, "-c", "print('test output line')"])
        time.sleep(1)
        log = runner.tail_log(run_id, 10)
        assert "test output line" in log

    def test_tail_log_empty_for_unknown(self, runner):
        assert runner.tail_log("nonexistent") == ""

    def test_log_path_returns_path(self, runner, run_id):
        runner.launch(run_id, [sys.executable, "-c", "print('x')"])
        path = runner.log_path(run_id)
        assert path is not None
        assert run_id in path
        time.sleep(1)

    def test_tail_log_flushes_for_running(self, runner, run_id):
        # Use -u for unbuffered stdout so output reaches the log file immediately
        runner.launch(
            run_id,
            [sys.executable, "-u", "-c", "import time; print('early'); time.sleep(5); print('late')"],
        )
        time.sleep(0.5)
        log = runner.tail_log(run_id, 10)
        assert "early" in log
        runner.stop(run_id)


class TestMetricParsing:
    def test_parse_wybe_metric_markers(self, runner, store, run_id):
        script = "print('##WYBE_METRIC:loss=0.5,step=100##')"
        runner.launch(run_id, [sys.executable, "-c", script])
        time.sleep(1)
        run = store.get_run(run_id)
        assert run["metrics"] is not None
        import json
        metrics = json.loads(run["metrics"])
        assert metrics["loss"] == 0.5
        assert metrics["step"] == 100

    def test_parse_string_metric(self, runner, store, run_id):
        script = "print('##WYBE_METRIC:model=resnet50##')"
        runner.launch(run_id, [sys.executable, "-c", script])
        time.sleep(1)
        run = store.get_run(run_id)
        import json
        metrics = json.loads(run["metrics"])
        assert metrics["model"] == "resnet50"


class TestReconnect:
    def test_reconnect_cleans_dead_runs(self, store, project_id, tmp_path):
        # Create a run that looks "running" but has an invalid PID
        rid = store.create_run(project_id, "training", {})
        store.update_run(rid, status="running", pid=99999999)

        runner = TaskRunner(store, log_dir=str(tmp_path / "logs"))
        cleaned = runner.reconnect_on_startup()
        assert rid in cleaned
        run = store.get_run(rid)
        assert run["status"] == "failed"

    def test_reconnect_leaves_alive_runs(self, store, project_id, tmp_path):
        import os
        # Use our own PID which is definitely alive
        rid = store.create_run(project_id, "training", {})
        store.update_run(rid, status="running", pid=os.getpid())

        runner = TaskRunner(store, log_dir=str(tmp_path / "logs"))
        cleaned = runner.reconnect_on_startup()
        assert rid not in cleaned
        run = store.get_run(rid)
        assert run["status"] == "running"


class TestResourceCleanup:
    def test_completed_process_removed_from_memory(self, runner, run_id):
        runner.launch(run_id, [sys.executable, "-c", "print('done')"])
        time.sleep(1)
        # After completion, _wait_for_exit should remove from _processes
        with runner._lock:
            assert run_id not in runner._processes

    def test_stopped_process_removed_from_memory(self, runner, run_id):
        runner.launch(run_id, [sys.executable, "-c", "import time; time.sleep(30)"])
        time.sleep(0.3)
        runner.stop(run_id)
        with runner._lock:
            assert run_id not in runner._processes
