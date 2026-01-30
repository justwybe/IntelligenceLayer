"""Manages the GROOT inference server lifecycle."""

import logging
from pathlib import Path
import sys
import threading

from frontend.services.process_manager import ProcessManager


logger = logging.getLogger(__name__)

# Lock for sys.path mutations
_sys_path_lock = threading.Lock()


class ServerManager:
    """Wraps ProcessManager for the GROOT inference server.

    Supports dynamic port configuration and exposes current server info
    so all tabs can reference it.
    """

    TASK_TYPE = "groot_server"

    def __init__(self, process_manager: ProcessManager, project_root: str = ""):
        self._pm = process_manager
        self.project_root = project_root or str(Path(__file__).resolve().parents[2])
        self.current_model_path: str = ""
        self.current_embodiment_tag: str = ""
        self.current_port: int = 5555

    def _ensure_project_on_path(self) -> None:
        """Add project root to sys.path if not already present (thread-safe)."""
        with _sys_path_lock:
            if self.project_root not in sys.path:
                sys.path.insert(0, self.project_root)

    def start(
        self,
        model_path: str,
        embodiment_tag: str,
        port: int = 5555,
        device: str = "cuda",
    ) -> str:
        if not model_path:
            return "Error: model_path is required"

        venv_python = str(Path(self.project_root) / ".venv" / "bin" / "python")
        cmd = [
            venv_python,
            "-m",
            "gr00t.eval.run_gr00t_server",
            "--model_path", model_path,
            "--embodiment_tag", embodiment_tag,
            "--port", str(port),
            "--device", device,
            "--host", "0.0.0.0",
        ]

        result = self._pm.launch(
            self.TASK_TYPE,
            cmd,
            cwd=self.project_root,
        )
        if "launched" in result:
            self.current_model_path = model_path
            self.current_embodiment_tag = embodiment_tag
            self.current_port = port
        return result

    def stop(self) -> str:
        # Try graceful kill via PolicyClient first
        try:
            self._ensure_project_on_path()
            from gr00t.policy.server_client import PolicyClient
            client = PolicyClient(
                host="localhost", port=self.current_port, timeout_ms=2000
            )
            client.kill_server()
        except Exception:
            pass

        result = self._pm.stop(self.TASK_TYPE)
        if "stopped" in result or "exited" in result:
            self.current_model_path = ""
            self.current_embodiment_tag = ""
        return result

    def ping(self) -> bool:
        try:
            self._ensure_project_on_path()
            from gr00t.policy.server_client import PolicyClient
            client = PolicyClient(
                host="localhost", port=self.current_port, timeout_ms=2000
            )
            return client.ping()
        except Exception:
            return False

    def status(self) -> str:
        return self._pm.status(self.TASK_TYPE)

    def tail_log(self, n_lines: int = 80) -> str:
        return self._pm.tail_log(self.TASK_TYPE, n_lines)

    def server_info(self) -> dict:
        """Return current server configuration for cross-tab use."""
        return {
            "model_path": self.current_model_path,
            "embodiment_tag": self.current_embodiment_tag,
            "port": self.current_port,
            "status": self.status(),
            "alive": self.ping() if self.status() == "running" else False,
        }
