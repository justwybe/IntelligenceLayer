"""SoulConfig — central configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class SoulConfig:
    """Configuration for the Wybe Soul System.

    All values can be overridden via SOUL_* environment variables.
    """

    # -- Anthropic API --
    anthropic_api_key: str = ""
    haiku_model: str = "claude-haiku-4-5-20251001"
    sonnet_model: str = "claude-sonnet-4-5-20250929"
    haiku_max_tokens: int = 256
    sonnet_max_tokens: int = 4096

    # -- Speech-to-Text --
    stt_enabled: bool = True
    whisper_model: str = "base"
    whisper_device: str = "cpu"

    # -- Text-to-Speech --
    tts_provider: str = "elevenlabs"  # "elevenlabs" or "pyttsx3"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    tts_rate: int = 150

    # -- GR00T --
    groot_host: str = "localhost"
    groot_port: int = 5555
    groot_enabled: bool = False

    # -- Memory --
    db_path: str = ""
    facility_name: str = "Wybe Care"

    # -- Interaction --
    silence_timeout: float = 2.0  # seconds of silence before processing
    interim_response: bool = True  # Haiku quick-ack for complex requests

    # -- Robot identity --
    robot_name: str = "Wybe"

    @classmethod
    def from_env(cls) -> SoulConfig:
        """Load config from SOUL_* environment variables."""

        def _env(key: str, default: str = "") -> str:
            return os.environ.get(f"SOUL_{key}", default)

        def _bool(key: str, default: bool = False) -> bool:
            val = _env(key, str(default)).lower()
            return val in ("true", "1", "yes")

        def _int(key: str, default: int = 0) -> int:
            try:
                return int(_env(key, str(default)))
            except ValueError:
                return default

        def _float(key: str, default: float = 0.0) -> float:
            try:
                return float(_env(key, str(default)))
            except ValueError:
                return default

        return cls(
            anthropic_api_key=_env("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", ""),
            haiku_model=_env("HAIKU_MODEL", cls.haiku_model),
            sonnet_model=_env("SONNET_MODEL", cls.sonnet_model),
            haiku_max_tokens=_int("HAIKU_MAX_TOKENS", cls.haiku_max_tokens),
            sonnet_max_tokens=_int("SONNET_MAX_TOKENS", cls.sonnet_max_tokens),
            stt_enabled=_bool("STT_ENABLED", cls.stt_enabled),
            whisper_model=_env("WHISPER_MODEL", cls.whisper_model),
            whisper_device=_env("WHISPER_DEVICE", cls.whisper_device),
            tts_provider=_env("TTS_PROVIDER", cls.tts_provider),
            elevenlabs_api_key=_env("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=_env("ELEVENLABS_VOICE_ID", cls.elevenlabs_voice_id),
            tts_rate=_int("TTS_RATE", cls.tts_rate),
            groot_host=_env("GROOT_HOST", cls.groot_host),
            groot_port=_int("GROOT_PORT", cls.groot_port),
            groot_enabled=_bool("GROOT_ENABLED", cls.groot_enabled),
            db_path=_env("DB_PATH"),
            facility_name=_env("FACILITY_NAME", cls.facility_name),
            silence_timeout=_float("SILENCE_TIMEOUT", cls.silence_timeout),
            interim_response=_bool("INTERIM_RESPONSE", cls.interim_response),
            robot_name=_env("ROBOT_NAME", cls.robot_name),
        )
