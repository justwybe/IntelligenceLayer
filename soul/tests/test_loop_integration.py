"""Integration tests — full pipeline with mocked external services."""

from unittest.mock import MagicMock, patch

import pytest

from soul.config import SoulConfig
from soul.loop import SoulLoop
from soul.cognition.schemas import (
    ActionPlan,
    ActionType,
    Action,
    Intent,
    IntentCategory,
    InteractionResult,
)


@pytest.fixture
def soul_config(db_path):
    return SoulConfig(
        anthropic_api_key="test-key",
        tts_provider="pyttsx3",
        groot_enabled=False,
        stt_enabled=False,
        db_path=db_path,
    )


@pytest.fixture
def soul_loop(soul_config):
    loop = SoulLoop(soul_config)
    yield loop
    loop.shutdown()


class TestSoulLoop:
    def test_init(self, soul_loop):
        assert soul_loop.config.anthropic_api_key == "test-key"
        assert soul_loop.store is not None
        assert soul_loop.residents is not None

    def test_start_and_end_conversation(self, soul_loop):
        cid = soul_loop.start_conversation()
        assert cid is not None
        soul_loop.end_conversation(summary="Test conversation")

    def test_set_resident(self, soul_loop):
        rid = soul_loop.residents.create(name="Martha", room="204")
        soul_loop.set_resident(rid)
        assert soul_loop._current_resident_id == rid

    def test_process_text_with_mocked_brain(self, soul_loop):
        """Full pipeline with mocked brain and dispatcher."""
        mock_brain = MagicMock()
        mock_brain.process.return_value = InteractionResult(
            intent=Intent(IntentCategory.GREETING, raw_text="Hello!"),
            response_text="Hello there! How are you today?",
            action_plan=ActionPlan.speak_only("Hello there! How are you today?"),
            model_used="haiku",
        )
        soul_loop._brain = mock_brain

        mock_dispatcher = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_dispatcher.execute.return_value = [mock_result]
        mock_dispatcher.speaker = MagicMock()
        soul_loop._dispatcher = mock_dispatcher

        soul_loop.start_conversation()
        result = soul_loop.process_text("Hello!")

        assert result["response_text"] == "Hello there! How are you today?"
        assert result["model_used"] == "haiku"
        assert result["intent"] == "greeting"
        assert result["actions_executed"] == 1

    def test_process_text_logs_task(self, soul_loop):
        """Verify interaction is logged in task history."""
        mock_brain = MagicMock()
        mock_brain.process.return_value = InteractionResult(
            intent=Intent(IntentCategory.SIMPLE_CHAT, raw_text="How's the weather?"),
            response_text="It's a lovely day!",
            action_plan=ActionPlan.speak_only("It's a lovely day!"),
            model_used="haiku",
        )
        soul_loop._brain = mock_brain

        mock_dispatcher = MagicMock()
        mock_dispatcher.execute.return_value = []
        mock_dispatcher.speaker = MagicMock()
        soul_loop._dispatcher = mock_dispatcher

        soul_loop.process_text("How's the weather?")

        tasks = soul_loop.task_logger.recent_tasks()
        assert len(tasks) == 1
        assert tasks[0]["task_type"] == "simple_chat"

    def test_process_text_with_interim_response(self, soul_loop):
        """Interim response should be spoken before main actions."""
        mock_brain = MagicMock()
        mock_brain.process.return_value = InteractionResult(
            intent=Intent(IntentCategory.COMPLEX_PLAN, raw_text="Get my glasses"),
            response_text="I'll get your glasses from room 204.",
            action_plan=ActionPlan(actions=[
                Action(ActionType.SPEAK, {"text": "On my way!"}),
                Action(ActionType.NAVIGATE, {"destination": "room_204"}, depends_on=[0]),
            ]),
            model_used="sonnet",
            interim_response="Sure, let me get your glasses!",
        )
        soul_loop._brain = mock_brain

        mock_dispatcher = MagicMock()
        mock_dispatcher.execute.return_value = [MagicMock(success=True), MagicMock(success=True)]
        soul_loop._dispatcher = mock_dispatcher

        result = soul_loop.process_text("Get my glasses")

        mock_dispatcher.speak.assert_called_once_with("Sure, let me get your glasses!")
        assert result["actions_executed"] == 2

    def test_shutdown(self, soul_loop):
        soul_loop.start_conversation()
        soul_loop.shutdown()
        assert soul_loop._running is False

    def test_conversation_messages_logged(self, soul_loop):
        """Messages in active conversation should be logged."""
        mock_brain = MagicMock()
        mock_brain.process.return_value = InteractionResult(
            intent=Intent(IntentCategory.GREETING, raw_text="Hi"),
            response_text="Hello!",
            action_plan=ActionPlan.speak_only("Hello!"),
            model_used="haiku",
        )
        soul_loop._brain = mock_brain

        mock_dispatcher = MagicMock()
        mock_dispatcher.execute.return_value = []
        mock_dispatcher.speaker = MagicMock()
        soul_loop._dispatcher = mock_dispatcher

        cid = soul_loop.start_conversation()
        soul_loop.process_text("Hi")

        messages = soul_loop.task_logger.get_conversation_messages(cid)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hi"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hello!"


class TestMemoryPersistence:
    """Test that memory persists across SoulLoop instances."""

    def test_resident_persists(self, soul_config):
        loop1 = SoulLoop(soul_config)
        rid = loop1.residents.create(name="Martha", room="204")
        loop1.shutdown()

        loop2 = SoulLoop(soul_config)
        r = loop2.residents.get(rid)
        assert r is not None
        assert r["name"] == "Martha"
        loop2.shutdown()

    def test_preferences_persist(self, soul_config):
        loop1 = SoulLoop(soul_config)
        rid = loop1.residents.create(name="Hans")
        loop1.preferences.set(rid, "drink", "coffee", "black")
        loop1.shutdown()

        loop2 = SoulLoop(soul_config)
        pref = loop2.preferences.get(rid, "drink", "coffee")
        assert pref is not None
        assert pref["value"] == "black"
        loop2.shutdown()
