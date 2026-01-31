"""Generic subprocess lifecycle manager for long-running tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import signal
import subprocess
import threading


logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    task_type: str
    process: subprocess.Popen
    log_path: Path
    log_file: object = field(default=None, repr=False)  # open file handle
    status: str = "running"  # running | completed | failed | stopped


class ProcessManager:
    """Thread-safe manager for launching and tracking subprocesses."""

    def __init__(self, log_dir: str | None = None):
        self._processes: dict[str, ProcessInfo] = {}
        self._lock = threading.Lock()
        if log_dir is None:
            base = os.environ.get(
                "WYBE_DATA_DIR", os.path.expanduser("~/.wybe_studio")
            )
            log_dir = os.path.join(base, "process_logs")
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _close_log_file(info: ProcessInfo) -> None:
        """Safely close the log file handle for a ProcessInfo."""
        try:
            if info.log_file and not getattr(info.log_file, "closed", True):
                info.log_file.close()
        except Exception:
            logger.debug("Failed to close log file for %s", info.task_type, exc_info=True)

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
                # Previous process finished — clean up stale entry
                self._close_log_file(info)

            if log_path is None:
                log_path = str(self._log_dir / f"{task_type}.log")

            resolved_log = Path(log_path)
            resolved_log.parent.mkdir(parents=True, exist_ok=True)

            proc_env = os.environ.copy()
            if env:
                proc_env.update(env)

            log_file = open(resolved_log, "w")  # noqa: SIM115
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
                log_file=log_file,
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

        # Close the log file handle
        self._close_log_file(info)

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
        except (ProcessLookupError, OSError):
            pass

        try:
            info.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(info.process.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
            try:
                info.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                logger.warning("%s: process did not exit after SIGKILL", task_type)

        # Close log file handle
        self._close_log_file(info)

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
        # Flush log so we read latest output
        try:
            if info.log_file and not getattr(info.log_file, "closed", True):
                info.log_file.flush()
        except Exception:
            logger.debug("Failed to flush log file for %s", task_type, exc_info=True)
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

    def cleanup_dead(self) -> list[str]:
        """Remove entries for processes that have exited. Returns cleaned task types."""
        cleaned = []
        with self._lock:
            dead = [
                k for k, v in self._processes.items()
                if v.process.poll() is not None
            ]
            for k in dead:
                info = self._processes.pop(k)
                self._close_log_file(info)
                cleaned.append(k)
        return cleaned
