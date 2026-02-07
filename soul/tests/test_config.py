"""Tests for SoulConfig."""

import os

from soul.config import SoulConfig


class TestSoulConfig:
    def test_defaults(self):
        config = SoulConfig()
        assert config.haiku_model == "claude-haiku-4-5-20251001"
        assert config.sonnet_model == "claude-sonnet-4-5-20250929"
        assert config.tts_provider == "elevenlabs"
        assert config.stt_enabled is True
        assert config.groot_enabled is False
        assert config.robot_name == "Wybe"
        assert config.silence_timeout == 2.0

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("SOUL_ANTHROPIC_API_KEY", "sk-test-123")
        monkeypatch.setenv("SOUL_TTS_PROVIDER", "pyttsx3")
        monkeypatch.setenv("SOUL_STT_ENABLED", "false")
        monkeypatch.setenv("SOUL_GROOT_ENABLED", "true")
        monkeypatch.setenv("SOUL_GROOT_PORT", "6666")
        monkeypatch.setenv("SOUL_ROBOT_NAME", "Buddy")
        monkeypatch.setenv("SOUL_SILENCE_TIMEOUT", "3.5")

        config = SoulConfig.from_env()
        assert config.anthropic_api_key == "sk-test-123"
        assert config.tts_provider == "pyttsx3"
        assert config.stt_enabled is False
        assert config.groot_enabled is True
        assert config.groot_port == 6666
        assert config.robot_name == "Buddy"
        assert config.silence_timeout == 3.5

    def test_from_env_fallback_anthropic_key(self, monkeypatch):
        """Falls back to ANTHROPIC_API_KEY if SOUL_ANTHROPIC_API_KEY not set."""
        monkeypatch.delenv("SOUL_ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fallback")

        config = SoulConfig.from_env()
        assert config.anthropic_api_key == "sk-fallback"

    def test_from_env_invalid_int(self, monkeypatch):
        monkeypatch.setenv("SOUL_GROOT_PORT", "not-a-number")
        config = SoulConfig.from_env()
        assert config.groot_port == 5555  # falls back to default

    def test_from_env_invalid_float(self, monkeypatch):
        monkeypatch.setenv("SOUL_SILENCE_TIMEOUT", "bad")
        config = SoulConfig.from_env()
        assert config.silence_timeout == 2.0
