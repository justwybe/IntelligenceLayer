from __future__ import annotations

"""Generic subprocess lifecycle manager for long-running tasks."""

import os
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProcessInfo:
    task_type: str
    process: subprocess.Popen
    log_path: Path
    status: str = "running"  # running | completed | failed | stopped


class ProcessManager:
    """Thread-safe manager for launching and tracking subprocesses."""

    def __init__(self, log_dir: str = "/tmp/intelligenceLayer_logs"):
        self._processes: dict[str, ProcessInfo] = {}
        self._lock = threading.Lock()
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def launch(
        self,
        task_type: str,
        cmd: list[str],
        log_path: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> str:
        """Start a subprocess, piping stdout/stderr to a log file.

        Returns a status message. Prevents duplicate launches of the same task_type.
        """
        with self._lock:
            if task_type in self._processes:
                info = self._processes[task_type]
                if info.process.poll() is None:
                    return f"{task_type} is already running (pid {info.process.pid})"
                # Previous process finished — allow relaunch

            if log_path is None:
                log_path = str(self._log_dir / f"{task_type}.log")

            resolved_log = Path(log_path)
            resolved_log.parent.mkdir(parents=True, exist_ok=True)

            proc_env = os.environ.copy()
            if env:
                proc_env.update(env)

            log_file = open(resolved_log, "w")
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=proc_env,
                    cwd=cwd,
                    preexec_fn=os.setsid,
                )
            except Exception as exc:
                log_file.close()
                return f"Failed to launch {task_type}: {exc}"

            self._processes[task_type] = ProcessInfo(
                task_type=task_type,
                process=proc,
                log_path=resolved_log,
            )

            # Background thread to update status when process exits
            t = threading.Thread(
                target=self._wait_for_exit, args=(task_type,), daemon=True
            )
            t.start()

            return f"{task_type} launched (pid {proc.pid})"

    def _wait_for_exit(self, task_type: str) -> None:
        with self._lock:
            info = self._processes.get(task_type)
        if info is None:
            return
        retcode = info.process.wait()
        with self._lock:
            if info.status == "running":
                info.status = "completed" if retcode == 0 else "failed"

    def stop(self, task_type: str) -> str:
        """Terminate gracefully, then kill after 5 seconds."""
        with self._lock:
            info = self._processes.get(task_type)
            if info is None:
                return f"{task_type} not found"
            if info.process.poll() is not None:
                return f"{task_type} already exited"

        # Send SIGTERM to the process group
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

        with self._lock:
            info.status = "stopped"
        return f"{task_type} stopped"

    def status(self, task_type: str) -> str:
        """Return running/completed/failed/stopped, or 'not found'."""
        with self._lock:
            info = self._processes.get(task_type)
            if info is None:
                return "not found"
            # Refresh status if still tracked as running
            if info.status == "running" and info.process.poll() is not None:
                info.status = (
                    "completed" if info.process.returncode == 0 else "failed"
                )
            return info.status

    def tail_log(self, task_type: str, n_lines: int = 80) -> str:
        """Read the last N lines of the log file for a task."""
        with self._lock:
            info = self._processes.get(task_type)
        if info is None:
            return ""
        try:
            text = info.log_path.read_text(errors="replace")
            lines = text.splitlines()
            return "\n".join(lines[-n_lines:])
        except FileNotFoundError:
            return ""

    def log_path(self, task_type: str) -> str | None:
        with self._lock:
            info = self._processes.get(task_type)
        return str(info.log_path) if info else None
