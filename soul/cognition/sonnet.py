"""SonnetEngine — structured planning via Anthropic Claude Sonnet.

Lazy-initializes the Anthropic client. Returns structured ActionPlan objects
parsed from the model's JSON output. Falls back to a speak-only plan on
parse failure.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

import anthropic

from soul.cognition.schemas import ActionPlan

if TYPE_CHECKING:
    from soul.config import SoulConfig

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code blocks.

    Handles:
    - Plain JSON
    - ```json ... ```
    - ``` ... ```
    """
    # Try to find JSON in a code block first
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Otherwise return the text as-is (assume it's raw JSON)
    return text.strip()


class SonnetEngine:
    """Structured planning engine using Claude Sonnet."""

    def __init__(self, config: SoulConfig):
        self._config = config
        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=self._config.anthropic_api_key,
            )
        return self._client

    def plan(self, text: str, system_prompt: str) -> ActionPlan:
        """Generate a structured action plan for a request.

        Args:
            text: The user's utterance.
            system_prompt: The fully-built Sonnet system prompt with context.

        Returns:
            An ActionPlan parsed from the model output. Falls back to a
            speak-only plan if JSON parsing fails.
        """
        client = self._get_client()
        response = client.messages.create(
            model=self._config.sonnet_model,
            max_tokens=self._config.sonnet_max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text

        try:
            json_str = _extract_json(raw)
            data = json.loads(json_str)
            plan = ActionPlan.from_dict(data)
            logger.debug("Sonnet plan: %d actions, reasoning: %s",
                         len(plan.actions), plan.reasoning)
            return plan
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Failed to parse Sonnet JSON, falling back to speak-only: %s",
                exc,
            )
            return ActionPlan.speak_only(
                "I understand your request. Let me see what I can do for you."
            )
