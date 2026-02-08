"""Whisper-based STT using faster-whisper for edge inference."""

from __future__ import annotations

import logging

from soul.stt.base import BaseSTT, Utterance

logger = logging.getLogger(__name__)


class WhisperSTT(BaseSTT):
    """Speech-to-text using faster-whisper (CTranslate2 backend).

    Runs on CPU by default (~200-400ms for base.en model).
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info(
                    "Whisper model loaded: %s on %s",
                    self._model_size,
                    self._device,
                )
            except ImportError:
                logger.error(
                    "faster-whisper not installed. "
                    "Install with: pip install faster-whisper"
                )
                raise
        return self._model

    def transcribe(self, audio_data: bytes) -> Utterance | None:
        import io

        model = self._get_model()

        # faster-whisper accepts file-like objects — avoid temp file I/O
        segments, info = model.transcribe(
            io.BytesIO(audio_data),
            beam_size=1,
            language="no",
            vad_filter=True,
        )

        text_parts = []
        total_duration = 0.0
        for segment in segments:
            text_parts.append(segment.text.strip())
            total_duration = max(total_duration, segment.end)

        full_text = " ".join(text_parts).strip()
        if not full_text:
            return None

        return Utterance(
            text=full_text,
            language=info.language,
            confidence=1.0 - info.language_probability
            if info.language != "en"
            else info.language_probability,
            duration=total_duration,
        )

    def is_available(self) -> bool:
        try:
            self._get_model()
            return True
        except Exception:
            return False
