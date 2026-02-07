"""Speaker — text-to-speech with ElevenLabs primary and pyttsx3 fallback.

Graceful degradation: if ElevenLabs is configured but fails at runtime,
automatically falls back to pyttsx3. If pyttsx3 also fails, logs the
error and continues silently (the robot should never crash because TTS
broke).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soul.config import SoulConfig

logger = logging.getLogger(__name__)


class Speaker:
    """Text-to-speech with ElevenLabs primary and pyttsx3 fallback."""

    def __init__(self, config: SoulConfig):
        self._config = config
        self._elevenlabs_client = None
        self._pyttsx3_engine = None

        # Try to initialise the configured provider
        if config.tts_provider == "elevenlabs" and config.elevenlabs_api_key:
            self._init_elevenlabs()

        # Always try to have pyttsx3 available as fallback
        self._init_pyttsx3()

    # -- initialisation helpers ------------------------------------------------

    def _init_elevenlabs(self) -> None:
        """Lazy-import and initialise the ElevenLabs client."""
        try:
            from elevenlabs import ElevenLabs  # type: ignore[import-untyped]

            self._elevenlabs_client = ElevenLabs(
                api_key=self._config.elevenlabs_api_key,
            )
            logger.info("ElevenLabs TTS initialised (voice=%s)", self._config.elevenlabs_voice_id)
        except ImportError:
            logger.warning("elevenlabs package not installed — will use pyttsx3 fallback")
        except Exception as exc:
            logger.warning("ElevenLabs init failed (%s) — will use pyttsx3 fallback", exc)

    def _init_pyttsx3(self) -> None:
        """Lazy-import and initialise the pyttsx3 engine."""
        try:
            import pyttsx3  # type: ignore[import-untyped]

            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", self._config.tts_rate)
            logger.info("pyttsx3 TTS initialised (rate=%d)", self._config.tts_rate)
        except ImportError:
            logger.warning("pyttsx3 package not installed — TTS will be unavailable")
        except Exception as exc:
            logger.warning("pyttsx3 init failed (%s) — TTS will be unavailable", exc)

    # -- public API ------------------------------------------------------------

    def speak(self, text: str) -> None:
        """Speak *text* using the best available TTS engine.

        Tries ElevenLabs first (if configured), falls back to pyttsx3,
        and ultimately logs a warning if neither works.
        """
        if not text:
            return

        # Try ElevenLabs
        if self._elevenlabs_client is not None:
            if self._speak_elevenlabs(text):
                return
            logger.warning("ElevenLabs failed at runtime — falling back to pyttsx3")

        # Try pyttsx3
        if self._pyttsx3_engine is not None:
            if self._speak_pyttsx3(text):
                return
            logger.warning("pyttsx3 failed at runtime — no TTS available")

        logger.warning("No TTS engine available — text not spoken: %s", text[:80])

    # -- private backends ------------------------------------------------------

    def _speak_elevenlabs(self, text: str) -> bool:
        """Attempt to speak via ElevenLabs. Returns True on success."""
        try:
            audio = self._elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=self._config.elevenlabs_voice_id,
                model_id="eleven_multilingual_v2",
            )
            # audio is a generator of bytes — consume it to play/save
            # In a real deployment this would stream to speakers.
            # For now, consume the iterator to confirm the API call worked.
            for _chunk in audio:
                pass
            return True
        except Exception as exc:
            logger.error("ElevenLabs TTS error: %s", exc)
            return False

    def _speak_pyttsx3(self, text: str) -> bool:
        """Attempt to speak via pyttsx3. Returns True on success."""
        try:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
            return True
        except Exception as exc:
            logger.error("pyttsx3 TTS error: %s", exc)
            return False
