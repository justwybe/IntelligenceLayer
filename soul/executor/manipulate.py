"""Manipulator — GR00T PolicyClient wrapper for manipulation actions.

Handles pick-up, put-down, and hand-over actions via the policy server.
Like Navigator, falls back to simulation mode when GR00T is disabled or
unavailable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from soul.config import SoulConfig

logger = logging.getLogger(__name__)


class Manipulator:
    """Send manipulation commands to the GR00T policy server."""

    def __init__(self, config: SoulConfig, client: Any | None = None):
        """Initialise the manipulator.

        Args:
            config: Soul system configuration.
            client: Optional pre-built PolicyClient instance. If *None* and
                    GR00T is enabled, the manipulator will attempt to create
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
            logger.warning("gr00t package not available — manipulation will run in simulation mode")
            return False
        except Exception as exc:
            logger.warning("Failed to connect to GR00T policy server: %s", exc)
            return False

    # -- public API ------------------------------------------------------------

    def execute(self, parameters: dict[str, Any]) -> bool:
        """Execute a manipulation action.

        Expected *parameters* keys:
            action: one of "pick_up", "put_down", "hand_over"
            target: the name of the object

        Returns True on success (or in simulation mode).
        """
        action = parameters.get("action", "unknown")
        target = parameters.get("target", "unknown")

        if not self._config.groot_enabled:
            logger.info("[SIM] Manipulate %s %s (simulation mode)", action, target)
            return True

        if not self._ensure_client():
            logger.info("[SIM] Manipulate %s %s (GR00T unavailable, simulating)", action, target)
            return True

        try:
            result = self._client.call_endpoint(
                "get_action",
                data={
                    "observation": {
                        "command": "manipulate",
                        "action": action,
                        "target": target,
                    }
                },
            )
            logger.info("Manipulation %s %s: %s", action, target, result)
            return True
        except Exception as exc:
            logger.error("Manipulation %s %s failed: %s", action, target, exc)
            return False
