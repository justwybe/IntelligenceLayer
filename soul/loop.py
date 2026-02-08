"""Main interaction loop: listen → think → act → remember.

This is the entry point for the Wybe Soul System. It continuously
listens for speech (or text input), processes it through the brain,
executes the action plan, and logs the interaction.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from soul.config import SoulConfig
from soul.memory.store import SoulStore
from soul.memory.residents import ResidentManager
from soul.memory.facility import FacilityManager
from soul.memory.preferences import PreferenceManager
from soul.memory.tasks import TaskLogger
from soul.stt.base import BaseSTT
from soul.stt.text_fallback import TextFallbackSTT

logger = logging.getLogger(__name__)


class SoulLoop:
    """Main interaction loop for the Wybe Soul System."""

    def __init__(self, config: SoulConfig | None = None):
        self.config = config or SoulConfig.from_env()
        self.store = SoulStore(db_path=self.config.db_path or None)
        self.residents = ResidentManager(self.store)
        self.facility = FacilityManager(self.store)
        self.preferences = PreferenceManager(self.store)
        self.task_logger = TaskLogger(self.store)

        # Lazy-init components (may fail if deps missing)
        self._brain = None
        self._dispatcher = None
        self._stt: BaseSTT | None = None
        self._speaker_id = None

        # State
        self._current_resident_id: str | None = None
        self._current_conversation_id: str | None = None
        self._running = False

    def _get_stt(self) -> BaseSTT:
        if self._stt is None:
            if self.config.stt_enabled:
                try:
                    from soul.stt.whisper_stt import WhisperSTT
                    stt = WhisperSTT(
                        model_size=self.config.whisper_model,
                        device=self.config.whisper_device,
                    )
                    if stt.is_available():
                        self._stt = stt
                        logger.info("Whisper STT initialized")
                    else:
                        logger.warning("Whisper not available, falling back to text input")
                        self._stt = TextFallbackSTT()
                except Exception as e:
                    logger.warning("Whisper init failed (%s), falling back to text input", e)
                    self._stt = TextFallbackSTT()
            else:
                self._stt = TextFallbackSTT()
        return self._stt

    def _get_brain(self):
        if self._brain is None:
            from soul.cognition.brain import SoulBrain
            self._brain = SoulBrain(
                config=self.config,
                store=self.store,
                residents=self.residents,
                facility=self.facility,
                preferences=self.preferences,
                task_logger=self.task_logger,
            )
        return self._brain

    def _get_dispatcher(self):
        if self._dispatcher is None:
            from soul.executor.dispatcher import Dispatcher
            from soul.executor.speak import Speaker
            from soul.executor.navigate import Navigator
            from soul.executor.manipulate import Manipulator

            self._dispatcher = Dispatcher(
                speaker=Speaker(self.config),
                navigator=Navigator(self.config),
                manipulator=Manipulator(self.config),
                preferences=self.preferences,
                resident_id=self._current_resident_id,
            )
        return self._dispatcher

    def _get_speaker_id(self):
        if self._speaker_id is None:
            from soul.stt.speaker_id import SpeakerIdentifier
            self._speaker_id = SpeakerIdentifier(
                self.store, self.config.speaker_id_threshold
            )
        return self._speaker_id

    def identify_speaker(self, audio_data: bytes) -> str | None:
        """Identify speaker from audio. Returns resident_id or None."""
        if not self.config.speaker_id_enabled:
            return None
        try:
            sid = self._get_speaker_id()
            if not sid.is_available():
                return None
            return sid.identify(audio_data)
        except Exception as exc:
            logger.warning("Speaker identification failed: %s", exc)
            return None

    def set_resident(self, resident_id: str | None) -> None:
        """Set the current resident for context."""
        self._current_resident_id = resident_id
        if resident_id:
            r = self.residents.get(resident_id)
            if r:
                logger.info("Active resident: %s", r["name"])

    def _build_history(self) -> list[dict]:
        """Build message history from the current conversation (capped at 20)."""
        if not self._current_conversation_id:
            return []
        raw = self.task_logger.get_conversation_messages(self._current_conversation_id)
        history = [{"role": m["role"], "content": m["content"]} for m in raw]
        return history[-20:]

    def process_text(self, text: str, skip_speak: bool = False) -> dict:
        """Process a text input through the full pipeline.

        If *skip_speak* is True, SPEAK actions and interim speech are skipped
        (useful when the caller handles audio output separately).

        Returns a dict with: response_text, actions_executed, model_used, intent.
        """
        brain = self._get_brain()
        dispatcher = self._get_dispatcher()

        # Build conversation history for multi-turn context
        history = self._build_history()

        # Think
        t0 = time.monotonic()
        result = brain.process(text, resident_id=self._current_resident_id, history=history)
        think_time = time.monotonic() - t0
        logger.info(
            "Brain processed in %.0fms: intent=%s model=%s",
            think_time * 1000,
            result.intent.category.value,
            result.model_used,
        )

        # Speak interim response if available (skip in web UI mode)
        if result.interim_response and not skip_speak:
            dispatcher.speak(result.interim_response)

        # Execute action plan
        t1 = time.monotonic()
        action_results = dispatcher.execute(result.action_plan, skip_speak=skip_speak)
        act_time = time.monotonic() - t1
        logger.info("Actions executed in %.0fms", act_time * 1000)

        # Remember — log task and conversation
        if self._current_conversation_id:
            self.task_logger.add_message(
                self._current_conversation_id, "user", text
            )
            self.task_logger.add_message(
                self._current_conversation_id, "assistant", result.response_text
            )

        self.task_logger.log_task(
            task_type=result.intent.category.value,
            description=text[:200],
            resident_id=self._current_resident_id,
            result=result.response_text[:500],
        )

        return {
            "response_text": result.response_text,
            "actions_executed": len(action_results),
            "actions_succeeded": sum(1 for r in action_results if r.success),
            "model_used": result.model_used,
            "intent": result.intent.category.value,
            "think_time_ms": round(think_time * 1000),
            "act_time_ms": round(act_time * 1000),
        }

    def start_conversation(self, resident_id: str | None = None) -> str:
        """Begin a new conversation, optionally with a known resident."""
        if resident_id:
            self.set_resident(resident_id)
        self._current_conversation_id = self.task_logger.start_conversation(
            resident_id=self._current_resident_id
        )
        return self._current_conversation_id

    def end_conversation(self, summary: str | None = None) -> None:
        """End the current conversation, auto-summarizing if no summary given."""
        if self._current_conversation_id:
            if summary is None:
                msgs = self.task_logger.get_conversation_messages(
                    self._current_conversation_id
                )
                if len(msgs) >= 2:
                    try:
                        brain = self._get_brain()
                        result = brain._haiku.summarize(
                            [{"role": m["role"], "content": m["content"]} for m in msgs]
                        )
                        if isinstance(result, str):
                            summary = result
                    except Exception as exc:
                        logger.warning("Failed to summarize conversation: %s", exc)
            self.task_logger.end_conversation(
                self._current_conversation_id, summary=summary
            )
            self._current_conversation_id = None

    def run_text_mode(self) -> None:
        """Run the interactive text-mode loop (for testing without audio)."""
        self._running = True
        robot_name = self.config.robot_name

        print(f"\n{'='*50}")
        print(f"  {robot_name} Soul System — Text Mode")
        print(f"{'='*50}")
        print("Type 'quit' to exit, 'resident <name>' to set active resident\n")

        self.start_conversation()

        while self._running:
            try:
                text = input(f"You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not text:
                continue
            if text.lower() == "quit":
                break
            if text.lower().startswith("resident "):
                name = text[9:].strip()
                r = self.residents.find_by_name(name)
                if r:
                    self.set_resident(r["id"])
                    print(f"[Active resident: {r['name']}, room {r.get('room', '?')}]")
                else:
                    print(f"[Resident '{name}' not found]")
                continue

            result = self.process_text(text)
            print(f"{robot_name}: {result['response_text']}")
            print(
                f"  [{result['intent']} | {result['model_used']} | "
                f"{result['think_time_ms']}ms think | "
                f"{result['actions_executed']} actions]"
            )

        self.end_conversation()
        print(f"\n{robot_name}: Goodbye! Take care.")

    def shutdown(self) -> None:
        """Clean shutdown."""
        self._running = False
        self.end_conversation()
        self.store.close()
        logger.info("Soul System shut down")


def main():
    """Entry point for the Soul System."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = SoulConfig.from_env()
    loop = SoulLoop(config)

    try:
        loop.run_text_mode()
    except KeyboardInterrupt:
        pass
    finally:
        loop.shutdown()


if __name__ == "__main__":
    main()
