"""Text passthrough STT — for testing and text-only mode."""

from __future__ import annotations

from soul.stt.base import BaseSTT, Utterance


class TextFallbackSTT(BaseSTT):
    """Passthrough that wraps raw text as an Utterance.

    Used when STT is disabled (SOUL_STT_ENABLED=false) or for testing.
    """

    def transcribe(self, audio_data: bytes) -> Utterance | None:
        text = audio_data.decode("utf-8", errors="replace").strip()
        if not text:
            return None
        return Utterance(text=text, confidence=1.0)

    def is_available(self) -> bool:
        return True
