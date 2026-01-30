from __future__ import annotations

"""TaskRunner — subprocess manager with DB-backed state tracking.

Replaces ProcessManager with WorkspaceStore integration so that run status,
metrics, and log paths persist across app restarts.
"""

import os
import re
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from frontend.services.workspace import WorkspaceStore


@dataclass
class ProcessInfo:
    run_id: str
    process: subprocess.Popen
    log_path: Path
    log_file: object  # open file handle


class TaskRunner:
    """Thread-safe subprocess manager backed by WorkspaceStore."""

    def __init__(self, store: WorkspaceStore, log_dir: str | None = None):
        self.store = store
        self._processes: dict[str, ProcessInfo] = {}
        self._lock = threading.Lock()
        if log_dir is None:
            base = os.environ.get(
                "WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio")
            )
            log_dir = os.path.join(base, "logs")
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # -- launching -------------------------------------------------------------

    def launch(self, run_id: str, cmd: list[str], cwd: str | None = None) -> str:
        """Launch subprocess for an existing run record.

        The run must already exist in the DB (created via WorkspaceStore.create_run).
        Returns a status message string.
        """
        with self._lock:
            if run_id in self._processes:
                info = self._processes[run_id]
                if info.process.poll() is None:
                    return f"Run {run_id} is already running (pid {info.process.pid})"

            log_path = self._log_dir / f"{run_id}.log"
            log_file = open(log_path, "w")

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=os.environ.copy(),
                    cwd=cwd,
                    preexec_fn=os.setsid,
                )
            except Exception as exc:
                log_file.close()
                self.store.update_run(run_id, status="failed")
                return f"Failed to launch run {run_id}: {exc}"

            self._processes[run_id] = ProcessInfo(
                run_id=run_id,
                process=proc,
                log_path=log_path,
                log_file=log_file,
            )

            self.store.update_run(
                run_id,
                status="running",
                started_at=datetime.now().isoformat(),
                log_path=str(log_path),
                pid=proc.pid,
            )

            t = threading.Thread(
                target=self._wait_for_exit, args=(run_id,), daemon=True
            )
            t.start()

            return f"Run {run_id} launched (pid {proc.pid})"

    def _wait_for_exit(self, run_id: str) -> None:
        with self._lock:
            info = self._processes.get(run_id)
        if info is None:
            return

        retcode = info.process.wait()
        info.log_file.close()

        # Parse structured markers from the log
        metrics = self._parse_markers(info.log_path)

        status = "completed" if retcode == 0 else "failed"
        updates: dict = {
            "status": status,
            "completed_at": datetime.now().isoformat(),
        }
        if metrics:
            updates["metrics"] = metrics

        self.store.update_run(run_id, **updates)

        # Log activity
        run = self.store.get_run(run_id)
        if run:
            self.store.log_activity(
                run["project_id"],
                f"run_{status}",
                "run",
                run_id,
                f"{run['run_type']} run {status}",
            )

    def _parse_markers(self, log_path: Path) -> dict:
        """Parse ##WYBE_METRIC:key=val,...## markers from log file."""
        metrics: dict = {}
        try:
            text = log_path.read_text(errors="replace")
            for m in re.finditer(r"##WYBE_METRIC:(.+?)##", text):
                for pair in m.group(1).split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        try:
                            metrics[k.strip()] = float(v.strip())
                        except ValueError:
                            metrics[k.strip()] = v.strip()
        except FileNotFoundError:
            pass
        return metrics

    # -- stopping --------------------------------------------------------------

    def stop(self, run_id: str) -> str:
        with self._lock:
            info = self._processes.get(run_id)
            if info is None:
                return f"Run {run_id} not found"
            if info.process.poll() is not None:
                return f"Run {run_id} already exited"

        try:
            os.killpg(os.getpgid(info.process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

        try:
            info.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(info.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            info.process.wait(timeout=3)

        self.store.update_run(
            run_id,
            status="stopped",
            completed_at=datetime.now().isoformat(),
        )
        return f"Run {run_id} stopped"

    # -- status / logs ---------------------------------------------------------

    def status(self, run_id: str) -> str:
        with self._lock:
            info = self._processes.get(run_id)
        if info is None:
            run = self.store.get_run(run_id)
            return run["status"] if run else "not found"
        if info.process.poll() is not None:
            run = self.store.get_run(run_id)
            return run["status"] if run else "completed"
        return "running"

    def tail_log(self, run_id: str, n_lines: int = 80) -> str:
        # First try in-memory process
        with self._lock:
            info = self._processes.get(run_id)
        if info is not None:
            log_path = info.log_path
        else:
            # Fall back to DB-stored path
            run = self.store.get_run(run_id)
            if run and run.get("log_path"):
                log_path = Path(run["log_path"])
            else:
                return ""
        try:
            text = log_path.read_text(errors="replace")
            lines = text.splitlines()
            return "\n".join(lines[-n_lines:])
        except FileNotFoundError:
            return ""

    def log_path(self, run_id: str) -> str | None:
        with self._lock:
            info = self._processes.get(run_id)
        if info:
            return str(info.log_path)
        run = self.store.get_run(run_id)
        return run.get("log_path") if run else None

    # -- reconnection on startup -----------------------------------------------

    def reconnect_on_startup(self) -> list[str]:
        """Check DB for runs marked 'running' and verify if their PIDs
        are still alive.  Mark dead processes as failed.

        Returns list of run_ids that were cleaned up.
        """
        cleaned: list[str] = []
        active = self.store.get_active_runs()
        for run in active:
            pid = run.get("pid")
            if pid is None:
                self.store.update_run(run["id"], status="failed")
                cleaned.append(run["id"])
                continue
            try:
                os.kill(pid, 0)  # signal 0 = check if alive
            except OSError:
                # Process is dead
                self.store.update_run(
                    run["id"],
                    status="failed",
                    completed_at=datetime.now().isoformat(),
                )
                cleaned.append(run["id"])
        return cleaned
