"""Tests for conversation memory — history, summaries, and auto-summarization."""

from unittest.mock import MagicMock, patch

import pytest

from soul.cognition.brain import SoulBrain
from soul.cognition.haiku import HaikuEngine
from soul.cognition.prompt import build_haiku_prompt
from soul.cognition.schemas import IntentCategory
from soul.config import SoulConfig
from soul.loop import SoulLoop
from soul.memory.tasks import TaskLogger


# =========================================================================
# HaikuEngine — history param
# =========================================================================


class TestHaikuHistory:

    @patch("soul.cognition.haiku.anthropic")
    def test_respond_with_history(self, mock_anthropic_mod, config):
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Yes, Martha, you mentioned your garden."
        mock_resp = MagicMock()
        mock_resp.content = [mock_content]
        mock_client.messages.create.return_value = mock_resp
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = HaikuEngine(config)
        history = [
            {"role": "user", "content": "I love my garden."},
            {"role": "assistant", "content": "That sounds lovely!"},
        ]
        result = engine.respond("Do you remember?", "system prompt", history=history)

        assert "Martha" in result or "garden" in result
        call_kwargs = mock_client.messages.create.call_args[1]
        # Should have 3 messages: 2 from history + 1 new
        assert len(call_kwargs["messages"]) == 3
        assert call_kwargs["messages"][0] == {"role": "user", "content": "I love my garden."}
        assert call_kwargs["messages"][2] == {"role": "user", "content": "Do you remember?"}

    @patch("soul.cognition.haiku.anthropic")
    def test_respond_without_history(self, mock_anthropic_mod, config):
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Hello!"
        mock_resp = MagicMock()
        mock_resp.content = [mock_content]
        mock_client.messages.create.return_value = mock_resp
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = HaikuEngine(config)
        engine.respond("Hi", "system prompt")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert len(call_kwargs["messages"]) == 1

    @patch("soul.cognition.haiku.anthropic")
    def test_summarize(self, mock_anthropic_mod, config):
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Beboeren ba om te og snakket om hagen sin."
        mock_resp = MagicMock()
        mock_resp.content = [mock_content]
        mock_client.messages.create.return_value = mock_resp
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = HaikuEngine(config)
        messages = [
            {"role": "user", "content": "Can I have some tea?"},
            {"role": "assistant", "content": "Of course! I'll get that for you."},
        ]
        summary = engine.summarize(messages)

        assert len(summary) > 0
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 128
        assert "Norwegian" in call_kwargs["system"] or "norsk" in call_kwargs["system"].lower()


# =========================================================================
# Prompt — conversation_summaries placeholder
# =========================================================================


class TestPromptConversationSummaries:

    def test_haiku_prompt_includes_summaries(self):
        prompt = build_haiku_prompt(
            robot_name="Wybe",
            facility_name="Wybe Care",
            resident_context="Resident: Martha",
            facility_context="Dining Hall",
            current_time="now",
            conversation_summaries="Previous conversations:\n- [yesterday]: Asked for tea.",
        )
        assert "Previous conversations" in prompt
        assert "Asked for tea" in prompt

    def test_haiku_prompt_empty_summaries(self):
        prompt = build_haiku_prompt(
            robot_name="Wybe",
            facility_name="Wybe Care",
            resident_context="",
            facility_context="",
            current_time="now",
            conversation_summaries="",
        )
        assert "Previous conversations" not in prompt


# =========================================================================
# TaskLogger — recent_summaries
# =========================================================================


class TestRecentSummaries:

    def test_recent_summaries_returns_only_summarized(self, store, task_logger):
        rid = store._new_id()
        store._conn.execute(
            "INSERT INTO residents (id, name) VALUES (?, ?)", (rid, "Martha")
        )
        store._conn.commit()

        # Create conversations with and without summaries
        cid1 = task_logger.start_conversation(rid)
        task_logger.end_conversation(cid1, summary="Asked for tea")

        cid2 = task_logger.start_conversation(rid)
        task_logger.end_conversation(cid2, summary=None)

        cid3 = task_logger.start_conversation(rid)
        task_logger.end_conversation(cid3, summary="Talked about garden")

        summaries = task_logger.recent_summaries(rid)
        assert len(summaries) == 2
        # Should be ordered by started_at DESC
        texts = [s["summary"] for s in summaries]
        assert "Talked about garden" in texts
        assert "Asked for tea" in texts

    def test_recent_summaries_respects_limit(self, store, task_logger):
        rid = store._new_id()
        store._conn.execute(
            "INSERT INTO residents (id, name) VALUES (?, ?)", (rid, "Hans")
        )
        store._conn.commit()

        for i in range(10):
            cid = task_logger.start_conversation(rid)
            task_logger.end_conversation(cid, summary=f"Conversation {i}")

        summaries = task_logger.recent_summaries(rid, limit=3)
        assert len(summaries) == 3


# =========================================================================
# SoulBrain — conversation summaries in prompt
# =========================================================================


class TestBrainConversationSummaries:

    def test_build_conversation_summaries_no_logger(self, config, store, residents, facility, preferences):
        brain = SoulBrain(
            config=config, store=store, residents=residents,
            facility=facility, preferences=preferences,
        )
        assert brain._build_conversation_summaries("some_id") == ""

    def test_build_conversation_summaries_no_resident(self, config, store, residents, facility, preferences, task_logger):
        brain = SoulBrain(
            config=config, store=store, residents=residents,
            facility=facility, preferences=preferences,
            task_logger=task_logger,
        )
        assert brain._build_conversation_summaries(None) == ""

    def test_build_conversation_summaries_with_data(self, config, store, residents, facility, preferences, task_logger):
        rid = residents.create(name="Martha", room="204")
        cid = task_logger.start_conversation(rid)
        task_logger.end_conversation(cid, summary="Talked about tea")

        brain = SoulBrain(
            config=config, store=store, residents=residents,
            facility=facility, preferences=preferences,
            task_logger=task_logger,
        )
        result = brain._build_conversation_summaries(rid)
        assert "Previous conversations:" in result
        assert "Talked about tea" in result


# =========================================================================
# SoulLoop — history building and auto-summarize
# =========================================================================


class TestLoopHistory:

    @pytest.fixture
    def soul_loop(self, db_path):
        config = SoulConfig(
            anthropic_api_key="test-key",
            stt_enabled=False,
            db_path=db_path,
        )
        loop = SoulLoop(config)
        yield loop
        loop.shutdown()

    def test_build_history_no_conversation(self, soul_loop):
        assert soul_loop._build_history() == []

    def test_build_history_with_messages(self, soul_loop):
        cid = soul_loop.start_conversation()
        soul_loop.task_logger.add_message(cid, "user", "Hello")
        soul_loop.task_logger.add_message(cid, "assistant", "Hi there!")

        history = soul_loop._build_history()
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}

    def test_build_history_capped_at_20(self, soul_loop):
        cid = soul_loop.start_conversation()
        for i in range(30):
            role = "user" if i % 2 == 0 else "assistant"
            soul_loop.task_logger.add_message(cid, role, f"Message {i}")

        history = soul_loop._build_history()
        assert len(history) == 20
        # Should be the last 20
        assert history[0]["content"] == "Message 10"

    @patch("soul.cognition.haiku.anthropic")
    def test_end_conversation_auto_summarizes(self, mock_anthropic_mod, soul_loop):
        mock_client = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Beboeren hilste og spurte om te."
        mock_resp = MagicMock()
        mock_resp.content = [mock_content]
        mock_client.messages.create.return_value = mock_resp
        mock_anthropic_mod.Anthropic.return_value = mock_client

        cid = soul_loop.start_conversation()
        soul_loop.task_logger.add_message(cid, "user", "Hello")
        soul_loop.task_logger.add_message(cid, "assistant", "Hi!")
        soul_loop.end_conversation()

        # Check that the conversation got a summary
        convos = soul_loop.task_logger.recent_conversations()
        assert len(convos) == 1
        assert convos[0]["summary"] is not None
        assert "Beboeren" in convos[0]["summary"]

    def test_end_conversation_explicit_summary(self, soul_loop):
        cid = soul_loop.start_conversation()
        soul_loop.task_logger.add_message(cid, "user", "Hello")
        soul_loop.task_logger.add_message(cid, "assistant", "Hi!")
        soul_loop.end_conversation(summary="Explicit summary")

        convos = soul_loop.task_logger.recent_conversations()
        assert convos[0]["summary"] == "Explicit summary"

    def test_end_conversation_skips_short_conversations(self, soul_loop):
        """Conversations with fewer than 2 messages should not be summarized."""
        cid = soul_loop.start_conversation()
        soul_loop.task_logger.add_message(cid, "user", "Hello")
        soul_loop.end_conversation()

        convos = soul_loop.task_logger.recent_conversations()
        assert convos[0]["summary"] is None
