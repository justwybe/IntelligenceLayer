"""TaskRunner — subprocess manager with DB-backed state tracking.

Replaces ProcessManager with WorkspaceStore integration so that run status,
metrics, and log paths persist across app restarts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import os
from pathlib import Path
import re
import signal
import subprocess
import threading

from frontend.services.workspace import WorkspaceStore


logger = logging.getLogger(__name__)


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
                # Previous process finished — clean up stale entry
                self._close_log_file(info)

            log_path = self._log_dir / f"{run_id}.log"
            log_file = open(log_path, "w")  # noqa: SIM115

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

    @staticmethod
    def _close_log_file(info: ProcessInfo) -> None:
        """Safely close the log file handle for a ProcessInfo."""
        try:
            if info.log_file and not getattr(info.log_file, "closed", True):
                info.log_file.close()
        except Exception:
            logger.debug("Failed to close log file for run %s", info.run_id, exc_info=True)

    def _wait_for_exit(self, run_id: str) -> None:
        with self._lock:
            info = self._processes.get(run_id)
        if info is None:
            return

        retcode = info.process.wait()

        # Flush and close the log file before reading it
        self._close_log_file(info)

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
        try:
            run = self.store.get_run(run_id)
            if run:
                self.store.log_activity(
                    run["project_id"],
                    f"run_{status}",
                    "run",
                    run_id,
                    f"{run['run_type']} run {status}",
                )
        except Exception:
            logger.exception("Failed to log activity for run %s", run_id)

        # Post-completion hooks
        if status == "completed":
            try:
                run = run or self.store.get_run(run_id)
                if run:
                    self._on_run_completed(run, info.log_path)
            except Exception:
                logger.exception("Post-completion hook failed for run %s", run_id)

        # Remove from in-memory dict to prevent unbounded growth
        with self._lock:
            self._processes.pop(run_id, None)

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

    def _on_run_completed(self, run: dict, log_path: Path) -> None:
        """Run post-completion hooks based on run type."""
        import json as _json

        run_type = run.get("run_type", "")
        project_id = run.get("project_id")
        config_raw = run.get("config", "{}")
        config = _json.loads(config_raw) if isinstance(config_raw, str) else config_raw

        if run_type == "conversion" and project_id:
            # Auto-register the converted dataset
            output_dir = config.get("output_dir", "")
            repo_id = config.get("repo_id", "")
            if output_dir:
                name = repo_id.replace("/", "_") if repo_id else Path(output_dir).name
                try:
                    self.store.register_dataset(
                        project_id=project_id,
                        name=name,
                        path=output_dir,
                        source="converted",
                    )
                    logger.info("Auto-registered converted dataset: %s", output_dir)
                except Exception:
                    logger.exception("Failed to auto-register dataset for run %s", run["id"])

        elif run_type == "benchmark" and project_id:
            # Auto-save benchmark evaluation record
            try:
                log_text = log_path.read_text(errors="replace")
                # Parse benchmark table for metrics
                metrics: dict = {}
                for line in log_text.splitlines():
                    if "E2E" in line and "|" in line and "Device" in line:
                        continue
                    if line.strip().startswith("|") and "E2E" not in line:
                        cells = [c.strip() for c in line.strip("|").split("|")]
                        if len(cells) >= 6:
                            try:
                                metrics["e2e_ms"] = float(cells[-2].replace("ms", "").strip())
                                metrics["frequency_hz"] = float(cells[-1].replace("Hz", "").strip())
                            except (ValueError, IndexError):
                                pass
                if metrics:
                    model_id = config.get("model_id", "")
                    self.store.save_evaluation(
                        run_id=run["id"],
                        model_id=model_id,
                        eval_type="benchmark",
                        metrics=metrics,
                    )
                    logger.info("Auto-saved benchmark evaluation for run %s", run["id"])
            except Exception:
                logger.exception("Failed to auto-save benchmark eval for run %s", run["id"])

    # -- stopping --------------------------------------------------------------

    def stop(self, run_id: str) -> str:
        with self._lock:
            info = self._processes.get(run_id)
            if info is None:
                return f"Run {run_id} not found"
            if info.process.poll() is not None:
                return f"Run {run_id} already exited"

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
                logger.warning("Run %s: process did not exit after SIGKILL", run_id)

        # Close log file handle
        self._close_log_file(info)

        self.store.update_run(
            run_id,
            status="stopped",
            completed_at=datetime.now().isoformat(),
        )

        # Remove from in-memory dict
        with self._lock:
            self._processes.pop(run_id, None)

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
            # Flush the log file so we can read latest output
            try:
                if info.log_file and not getattr(info.log_file, "closed", True):
                    info.log_file.flush()
            except Exception:
                logger.debug("Failed to flush log file for run %s", run_id, exc_info=True)
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
        if cleaned:
            logger.info("Cleaned up %d stale runs on startup: %s", len(cleaned), cleaned)
        return cleaned
