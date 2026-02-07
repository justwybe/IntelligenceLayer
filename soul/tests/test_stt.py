"""Tests for STT layer — text fallback and Whisper (mocked)."""

from unittest.mock import MagicMock, patch

from soul.stt.base import Utterance
from soul.stt.text_fallback import TextFallbackSTT


class TestTextFallbackSTT:
    def test_transcribe_text(self):
        stt = TextFallbackSTT()
        result = stt.transcribe(b"Hello there!")
        assert result is not None
        assert result.text == "Hello there!"
        assert result.confidence == 1.0

    def test_transcribe_empty(self):
        stt = TextFallbackSTT()
        assert stt.transcribe(b"") is None
        assert stt.transcribe(b"   ") is None

    def test_is_available(self):
        stt = TextFallbackSTT()
        assert stt.is_available() is True

    def test_unicode(self):
        stt = TextFallbackSTT()
        result = stt.transcribe("Guten Tag!".encode("utf-8"))
        assert result.text == "Guten Tag!"


class TestUtterance:
    def test_defaults(self):
        u = Utterance(text="Hi")
        assert u.language == "en"
        assert u.confidence == 1.0
        assert u.duration == 0.0


class TestWhisperSTT:
    def test_is_available_no_package(self):
        """When faster-whisper is not installed, is_available returns False."""
        with patch.dict("sys.modules", {"faster_whisper": None}):
            from soul.stt.whisper_stt import WhisperSTT
            stt = WhisperSTT()
            # Reset cached model
            stt._model = None
            assert stt.is_available() is False

    def test_transcribe_with_mock(self):
        """Test transcription with a mocked WhisperModel."""
        from soul.stt.whisper_stt import WhisperSTT

        stt = WhisperSTT()

        mock_segment = MagicMock()
        mock_segment.text = " Hello, how are you? "
        mock_segment.end = 2.5

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.98

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        stt._model = mock_model

        result = stt.transcribe(b"fake wav data")
        assert result is not None
        assert result.text == "Hello, how are you?"
        assert result.duration == 2.5

    def test_transcribe_empty_audio(self):
        """When no speech detected, returns None."""
        from soul.stt.whisper_stt import WhisperSTT

        stt = WhisperSTT()

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.5

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)
        stt._model = mock_model

        result = stt.transcribe(b"silence")
        assert result is None
