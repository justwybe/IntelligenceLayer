"""Tests for ProcessManager — generic subprocess lifecycle manager."""

from __future__ import annotations

import sys
import time

import pytest

from frontend.services.process_manager import ProcessManager


@pytest.fixture
def pm(tmp_path):
    """Provide a ProcessManager with a temp log directory."""
    return ProcessManager(log_dir=str(tmp_path / "logs"))


class TestLaunch:
    def test_launch_simple(self, pm):
        msg = pm.launch("test_task", [sys.executable, "-c", "print('hello')"])
        assert "launched" in msg
        time.sleep(1)
        assert pm.status("test_task") == "completed"

    def test_launch_duplicate_prevented(self, pm):
        pm.launch("sleeper", [sys.executable, "-c", "import time; time.sleep(5)"])
        msg = pm.launch("sleeper", [sys.executable, "-c", "print('dup')"])
        assert "already running" in msg
        pm.stop("sleeper")

    def test_launch_invalid_command(self, pm):
        msg = pm.launch("bad", ["/nonexistent/binary"])
        assert "Failed to launch" in msg

    def test_launch_with_custom_env(self, pm):
        msg = pm.launch(
            "env_test",
            [sys.executable, "-c", "import os; print(os.environ.get('CUSTOM_VAR', ''))"],
            env={"CUSTOM_VAR": "test_value"},
        )
        assert "launched" in msg
        time.sleep(1)
        log = pm.tail_log("env_test")
        assert "test_value" in log

    def test_launch_reuses_after_completion(self, pm):
        pm.launch("reuse", [sys.executable, "-c", "print('first')"])
        time.sleep(1)
        assert pm.status("reuse") == "completed"
        msg = pm.launch("reuse", [sys.executable, "-c", "print('second')"])
        assert "launched" in msg
        time.sleep(1)
        log = pm.tail_log("reuse")
        assert "second" in log


class TestStop:
    def test_stop_running(self, pm):
        pm.launch("to_stop", [sys.executable, "-c", "import time; time.sleep(30)"])
        time.sleep(0.3)
        msg = pm.stop("to_stop")
        assert "stopped" in msg
        assert pm.status("to_stop") == "stopped"

    def test_stop_unknown(self, pm):
        msg = pm.stop("nonexistent")
        assert "not found" in msg

    def test_stop_already_exited(self, pm):
        pm.launch("done", [sys.executable, "-c", "print('done')"])
        time.sleep(1)
        msg = pm.stop("done")
        assert "already exited" in msg


class TestStatus:
    def test_status_not_found(self, pm):
        assert pm.status("nonexistent") == "not found"

    def test_status_running(self, pm):
        pm.launch("running_task", [sys.executable, "-c", "import time; time.sleep(5)"])
        assert pm.status("running_task") == "running"
        pm.stop("running_task")

    def test_status_failed(self, pm):
        pm.launch("fail_task", [sys.executable, "-c", "import sys; sys.exit(1)"])
        time.sleep(1)
        assert pm.status("fail_task") == "failed"


class TestLogs:
    def test_tail_log(self, pm):
        pm.launch("log_task", [sys.executable, "-c", "print('log output')"])
        time.sleep(1)
        log = pm.tail_log("log_task")
        assert "log output" in log

    def test_tail_log_unknown(self, pm):
        assert pm.tail_log("nonexistent") == ""

    def test_log_path(self, pm):
        pm.launch("path_task", [sys.executable, "-c", "print('x')"])
        path = pm.log_path("path_task")
        assert path is not None
        assert "path_task" in path
        time.sleep(1)

    def test_tail_log_flushes(self, pm):
        pm.launch(
            "flush_task",
            [sys.executable, "-c", "import time; print('early', flush=True); time.sleep(5)"],
        )
        time.sleep(0.5)
        log = pm.tail_log("flush_task")
        assert "early" in log
        pm.stop("flush_task")


class TestCleanupDead:
    def test_cleanup_removes_exited(self, pm):
        pm.launch("dead1", [sys.executable, "-c", "print('done')"])
        pm.launch("dead2", [sys.executable, "-c", "print('done')"])
        time.sleep(1)
        cleaned = pm.cleanup_dead()
        assert "dead1" in cleaned
        assert "dead2" in cleaned
        # After cleanup, status returns "not found"
        assert pm.status("dead1") == "not found"

    def test_cleanup_keeps_running(self, pm):
        pm.launch("alive", [sys.executable, "-c", "import time; time.sleep(10)"])
        pm.launch("dead", [sys.executable, "-c", "print('done')"])
        time.sleep(1)
        cleaned = pm.cleanup_dead()
        assert "dead" in cleaned
        assert "alive" not in cleaned
        assert pm.status("alive") == "running"
        pm.stop("alive")
