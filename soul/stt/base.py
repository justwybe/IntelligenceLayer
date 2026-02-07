"""Abstract STT interface and shared types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Utterance:
    """A transcribed speech utterance."""

    text: str
    language: str = "en"
    confidence: float = 1.0
    duration: float = 0.0  # seconds


class BaseSTT(ABC):
    """Abstract interface for speech-to-text engines."""

    @abstractmethod
    def transcribe(self, audio_data: bytes) -> Utterance | None:
        """Transcribe raw audio bytes into text.

        Returns None if no speech was detected.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the STT engine is ready."""
