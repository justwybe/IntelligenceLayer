"""HaikuEngine — fast conversational responses via Anthropic Claude Haiku.

Lazy-initializes the Anthropic client. Designed for quick, warm responses
in the care-home companion context.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import anthropic

if TYPE_CHECKING:
    from soul.config import SoulConfig

logger = logging.getLogger(__name__)


class HaikuEngine:
    """Fast conversational engine using Claude Haiku."""

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

    @staticmethod
    def _cached_system(system_prompt: str) -> list[dict]:
        """Wrap system prompt in a cache_control block for prompt caching."""
        return [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    def respond(
        self, text: str, system_prompt: str, history: list[dict] | None = None
    ) -> str:
        """Generate a conversational response.

        Args:
            text: The user's utterance.
            system_prompt: The fully-built system prompt with context injected.
            history: Optional prior messages ``[{"role": ..., "content": ...}, ...]``.

        Returns:
            The model's text response.

        Raises:
            anthropic.APIError: On API failure (fail-fast, no retries).
        """
        client = self._get_client()
        messages = list(history or [])
        messages.append({"role": "user", "content": text})
        response = client.messages.create(
            model=self._config.haiku_model,
            max_tokens=self._config.haiku_max_tokens,
            system=self._cached_system(system_prompt),
            messages=messages,
        )
        return response.content[0].text

    def acknowledge(self, text: str, system_prompt: str) -> str:
        """Generate a quick interim acknowledgment for complex requests.

        Args:
            text: The user's utterance being processed.
            system_prompt: The acknowledgment system prompt.

        Returns:
            A brief, warm acknowledgment string.
        """
        client = self._get_client()
        response = client.messages.create(
            model=self._config.haiku_model,
            max_tokens=256,  # Keep acknowledgments very short
            system=self._cached_system(system_prompt),
            messages=[{"role": "user", "content": text}],
        )
        return response.content[0].text

    def summarize(self, messages: list[dict]) -> str:
        """Summarize a conversation into 1-2 sentences."""
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        client = self._get_client()
        response = client.messages.create(
            model=self._config.haiku_model,
            max_tokens=128,
            system="Summarize this care-home conversation in 1-2 sentences in Norwegian. "
            "Focus on what the resident wanted and any preferences learned.",
            messages=[{"role": "user", "content": transcript}],
        )
        return response.content[0].text
