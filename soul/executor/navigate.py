"""Navigator — GR00T PolicyClient wrapper for navigation commands.

When GR00T is enabled, sends navigation commands to the policy server.
When disabled (the default on macOS dev machines), runs in simulation
mode and always returns success.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from soul.config import SoulConfig

logger = logging.getLogger(__name__)


class Navigator:
    """Send navigation commands to the GR00T policy server."""

    def __init__(self, config: SoulConfig, client: Any | None = None):
        """Initialise the navigator.

        Args:
            config: Soul system configuration.
            client: Optional pre-built PolicyClient instance. If *None* and
                    GR00T is enabled, the navigator will attempt to create
                    its own client on first use.
        """
        self._config = config
        self._client = client

    # -- lazy client creation --------------------------------------------------

    def _ensure_client(self) -> bool:
        """Ensure a PolicyClient is available. Returns False if unavailable."""
        if self._client is not None:
            return True

        if not self._config.groot_enabled:
            return False

        try:
            from gr00t.policy.server_client import PolicyClient  # type: ignore[import-untyped]

            self._client = PolicyClient(
                host=self._config.groot_host,
                port=self._config.groot_port,
            )
            logger.info(
                "Connected to GR00T policy server at %s:%d",
                self._config.groot_host,
                self._config.groot_port,
            )
            return True
        except ImportError:
            logger.warning("gr00t package not available — navigation will run in simulation mode")
            return False
        except Exception as exc:
            logger.warning("Failed to connect to GR00T policy server: %s", exc)
            return False

    # -- public API ------------------------------------------------------------

    def navigate(self, destination: str) -> bool:
        """Navigate to *destination*.

        Returns True on success (or in simulation mode).
        """
        if not self._config.groot_enabled:
            logger.info("[SIM] Navigate to %s (simulation mode)", destination)
            return True

        if not self._ensure_client():
            logger.info("[SIM] Navigate to %s (GR00T unavailable, simulating)", destination)
            return True

        try:
            result = self._client.call_endpoint(
                "get_action",
                data={"observation": {"command": "navigate", "destination": destination}},
            )
            logger.info("Navigation to %s: %s", destination, result)
            return True
        except Exception as exc:
            logger.error("Navigation to %s failed: %s", destination, exc)
            return False
