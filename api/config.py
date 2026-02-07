"""API configuration via Pydantic Settings."""

from __future__ import annotations

import os
import uuid

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env file."""

    wybe_api_key: str = ""
    db_path: str = os.path.join(os.path.expanduser("~/.wybe_studio"), "studio.db")
    project_root: str = os.environ.get("PROJECT_DIR", "/root/IntelligenceLayer")
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    gpu_broadcast_interval: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def get_origins(self) -> list[str]:
        """Return allowed origins, auto-adding RunPod proxy if on a pod."""
        origins = list(self.allowed_origins)
        pod_id = os.environ.get("RUNPOD_POD_ID") or os.environ.get("HOSTNAME", "")
        if pod_id and "." not in pod_id:
            origins.append(f"https://{pod_id}-3000.proxy.runpod.net")
            origins.append(f"https://{pod_id}-8000.proxy.runpod.net")
        return origins

    def ensure_api_key(self) -> str:
        """Return existing key or auto-generate one and write to .env."""
        if self.wybe_api_key:
            return self.wybe_api_key

        key = uuid.uuid4().hex
        self.wybe_api_key = key

        env_path = os.path.join(self.project_root, ".env")
        with open(env_path, "a") as f:
            f.write(f"\nWYBE_API_KEY={key}\n")

        return key


settings = Settings()
