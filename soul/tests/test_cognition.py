"""Tests for HaikuEngine, SonnetEngine, and SoulBrain with mocked Anthropic API."""

import json
from unittest.mock import MagicMock, patch

import pytest

from soul.cognition.brain import SoulBrain
from soul.cognition.haiku import HaikuEngine
from soul.cognition.prompt import (
    build_acknowledge_prompt,
    build_haiku_prompt,
    build_sonnet_prompt,
)
from soul.cognition.schemas import (
    ActionPlan,
    ActionType,
    IntentCategory,
    InteractionResult,
)
from soul.cognition.sonnet import SonnetEngine, _extract_json
from soul.config import SoulConfig


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def mock_anthropic_response():
    """Factory for building mock Anthropic API responses."""
    def _make(text: str):
        mock_content = MagicMock()
        mock_content.text = text
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response
    return _make


@pytest.fixture
def mock_client(mock_anthropic_response):
    """A mock Anthropic client whose messages.create returns configurable text."""
    client = MagicMock()
    # Default response
    client.messages.create.return_value = mock_anthropic_response("Hello, Martha!")
    return client


# =========================================================================
# Prompt builder tests
# =========================================================================

class TestPromptBuilders:

    def test_haiku_prompt_has_placeholders_filled(self):
        prompt = build_haiku_prompt(
            robot_name="Wybe",
            facility_name="Sunrise Care",
            resident_context="Resident: Martha\nRoom: 204",
            facility_context="Dining Hall on floor 1",
            current_time="Monday, January 6, 2025 at 10:00 AM",
        )
        assert "Wybe" in prompt
        assert "Sunrise Care" in prompt
        assert "Martha" in prompt
        assert "Dining Hall" in prompt
        assert "Monday" in prompt

    def test_sonnet_prompt_has_json_format(self):
        prompt = build_sonnet_prompt(
            robot_name="Wybe",
            facility_name="Wybe Care",
            resident_context="",
            facility_context="",
            current_time="now",
        )
        assert "action_type" in prompt
        assert "parameters" in prompt
        assert "priority" in prompt
        assert "depends_on" in prompt
        assert "reasoning" in prompt

    def test_acknowledge_prompt_is_brief(self):
        prompt = build_acknowledge_prompt(
            robot_name="Wybe",
            facility_name="Wybe Care",
            resident_context="Resident: Martha",
        )
        assert "brief" in prompt.lower() or "1 sentence" in prompt.lower()

    def test_default_contexts_when_empty(self):
        prompt = build_haiku_prompt(
            robot_name="Wybe",
            facility_name="Wybe Care",
            resident_context="",
            facility_context="",
            current_time="now",
        )
        assert "No resident identified" in prompt
        assert "No facility map available" in prompt


# =========================================================================
# HaikuEngine tests
# =========================================================================

class TestHaikuEngine:

    def test_lazy_init(self, config):
        engine = HaikuEngine(config)
        assert engine._client is None

    @patch("soul.cognition.haiku.anthropic")
    def test_respond(self, mock_anthropic_mod, config, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Good morning, Martha! How lovely to see you today."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = HaikuEngine(config)
        result = engine.respond("Good morning!", "You are Wybe.")

        assert "Martha" in result
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == config.haiku_model
        assert call_kwargs["system"] == "You are Wybe."

    @patch("soul.cognition.haiku.anthropic")
    def test_acknowledge(self, mock_anthropic_mod, config, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Of course, Martha, let me work on that for you."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = HaikuEngine(config)
        result = engine.acknowledge("Can you plan a party?", "Quick ack prompt.")

        assert "Martha" in result
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 256  # Short ack

    @patch("soul.cognition.haiku.anthropic")
    def test_client_initialized_once(self, mock_anthropic_mod, config):
        mock_anthropic_mod.Anthropic.return_value = MagicMock()
        mock_anthropic_mod.Anthropic.return_value.messages.create.return_value = MagicMock(
            content=[MagicMock(text="hi")]
        )

        engine = HaikuEngine(config)
        engine.respond("a", "b")
        engine.respond("c", "d")

        # Client should only be created once (lazy singleton)
        mock_anthropic_mod.Anthropic.assert_called_once()


# =========================================================================
# SonnetEngine tests
# =========================================================================

class TestSonnetEngine:

    def test_extract_json_plain(self):
        raw = '{"actions": [], "reasoning": "test"}'
        assert _extract_json(raw) == raw

    def test_extract_json_code_block(self):
        raw = '```json\n{"actions": [], "reasoning": "test"}\n```'
        assert _extract_json(raw) == '{"actions": [], "reasoning": "test"}'

    def test_extract_json_code_block_no_lang(self):
        raw = '```\n{"actions": []}\n```'
        assert _extract_json(raw) == '{"actions": []}'

    @patch("soul.cognition.sonnet.anthropic")
    def test_plan_valid_json(self, mock_anthropic_mod, config, mock_anthropic_response):
        plan_json = json.dumps({
            "actions": [
                {
                    "action_type": "speak",
                    "parameters": {"text": "I'll get your glasses, Martha."},
                    "priority": 1,
                    "depends_on": [],
                },
                {
                    "action_type": "navigate",
                    "parameters": {"destination": "Room 204", "reason": "fetch glasses"},
                    "priority": 2,
                    "depends_on": [0],
                },
            ],
            "reasoning": "Martha needs her glasses from her room.",
        })

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(plan_json)
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = SonnetEngine(config)
        plan = engine.plan("Bring me my glasses", "Sonnet prompt here.")

        assert len(plan.actions) == 2
        assert plan.actions[0].action_type == ActionType.SPEAK
        assert plan.actions[1].action_type == ActionType.NAVIGATE
        assert "glasses" in plan.reasoning.lower()

    @patch("soul.cognition.sonnet.anthropic")
    def test_plan_wrapped_in_code_block(self, mock_anthropic_mod, config, mock_anthropic_response):
        plan_json = '```json\n' + json.dumps({
            "actions": [
                {"action_type": "speak", "parameters": {"text": "Sure!"}, "priority": 1}
            ],
            "reasoning": "Simple response.",
        }) + '\n```'

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(plan_json)
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = SonnetEngine(config)
        plan = engine.plan("Test", "prompt")

        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == ActionType.SPEAK

    @patch("soul.cognition.sonnet.anthropic")
    def test_plan_fallback_on_bad_json(self, mock_anthropic_mod, config, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Sorry, I can't do that right now."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = SonnetEngine(config)
        plan = engine.plan("Do something complex", "prompt")

        # Should fallback to a speak-only plan
        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == ActionType.SPEAK

    @patch("soul.cognition.sonnet.anthropic")
    def test_plan_uses_sonnet_model(self, mock_anthropic_mod, config, mock_anthropic_response):
        plan_json = json.dumps({
            "actions": [{"action_type": "speak", "parameters": {"text": "ok"}}],
            "reasoning": "test",
        })
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(plan_json)
        mock_anthropic_mod.Anthropic.return_value = mock_client

        engine = SonnetEngine(config)
        engine.plan("test", "prompt")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == config.sonnet_model


# =========================================================================
# SoulBrain orchestration tests
# =========================================================================

class TestSoulBrain:

    @pytest.fixture
    def brain(self, config, store, residents, facility, preferences):
        return SoulBrain(
            config=config,
            store=store,
            residents=residents,
            facility=facility,
            preferences=preferences,
        )

    @patch("soul.cognition.haiku.anthropic")
    def test_greeting_uses_haiku_only(
        self, mock_anthropic_mod, brain, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Hello! It's wonderful to see you today."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("Hello!")

        assert isinstance(result, InteractionResult)
        assert result.intent.category == IntentCategory.GREETING
        assert result.model_used == brain._config.haiku_model
        assert "wonderful" in result.response_text.lower() or "hello" in result.response_text.lower()
        # Only Haiku should be called
        assert mock_client.messages.create.call_count == 1

    @patch("soul.cognition.sonnet.anthropic")
    @patch("soul.cognition.haiku.anthropic")
    def test_item_request_uses_both_engines(
        self,
        mock_haiku_mod,
        mock_sonnet_mod,
        brain,
        mock_anthropic_response,
    ):
        # Haiku for ack
        haiku_client = MagicMock()
        haiku_client.messages.create.return_value = mock_anthropic_response(
            "Of course! Let me get that for you."
        )
        mock_haiku_mod.Anthropic.return_value = haiku_client

        # Sonnet for plan
        plan_json = json.dumps({
            "actions": [
                {"action_type": "speak", "parameters": {"text": "I'll fetch your glasses."}},
                {"action_type": "navigate", "parameters": {"destination": "Room 204"}},
                {"action_type": "manipulate", "parameters": {"object": "glasses", "action": "pick_up"}},
            ],
            "reasoning": "Fetch glasses from room 204.",
        })
        sonnet_client = MagicMock()
        sonnet_client.messages.create.return_value = mock_anthropic_response(plan_json)
        mock_sonnet_mod.Anthropic.return_value = sonnet_client

        result = brain.process("Bring me my glasses")

        assert result.intent.category == IntentCategory.REQUEST_ITEM
        assert result.model_used == brain._config.sonnet_model
        assert result.interim_response is not None  # Haiku ack
        assert len(result.action_plan.actions) == 3

    @patch("soul.cognition.haiku.anthropic")
    def test_emergency_creates_alert_action(
        self, mock_anthropic_mod, brain, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Stay calm, Martha. I'm alerting the staff right now."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("Help! I've fallen!")

        assert result.intent.category == IntentCategory.EMERGENCY
        # Should have alert_staff action
        action_types = [a.action_type for a in result.action_plan.actions]
        assert ActionType.ALERT_STAFF in action_types
        assert ActionType.SPEAK in action_types
        # Alert should be critical urgency
        alert = [a for a in result.action_plan.actions if a.action_type == ActionType.ALERT_STAFF][0]
        assert alert.parameters["urgency"] == "critical"

    @patch("soul.cognition.haiku.anthropic")
    def test_farewell_uses_haiku(
        self, mock_anthropic_mod, brain, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Goodbye! Have a lovely evening."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("Goodbye, see you tomorrow")

        assert result.intent.category == IntentCategory.FAREWELL
        assert result.model_used == brain._config.haiku_model

    @patch("soul.cognition.haiku.anthropic")
    def test_process_with_resident_id(
        self, mock_anthropic_mod, brain, sample_resident, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Good morning, Martha! How are you today?"
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("Good morning!", resident_id=sample_resident)

        assert result.resident_id == sample_resident
        # The system prompt should have been built with resident context
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "Martha" in call_kwargs["system"]

    @patch("soul.cognition.haiku.anthropic")
    def test_emergency_with_haiku_failure_still_works(
        self, mock_anthropic_mod, brain
    ):
        """Emergency must produce a result even if Haiku API fails."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API down")
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("Help! Emergency!")

        assert result.intent.category == IntentCategory.EMERGENCY
        # Should have a fallback response
        assert "help" in result.response_text.lower() or "calm" in result.response_text.lower()
        # Alert action should still be there
        action_types = [a.action_type for a in result.action_plan.actions]
        assert ActionType.ALERT_STAFF in action_types

    @patch("soul.cognition.sonnet.anthropic")
    @patch("soul.cognition.haiku.anthropic")
    def test_complex_plan_with_disabled_interim(
        self, mock_haiku_mod, mock_sonnet_mod, config, store, residents,
        facility, preferences, mock_anthropic_response,
    ):
        """When interim_response is disabled, Haiku ack should be skipped."""
        config_no_interim = SoulConfig(
            anthropic_api_key="test-key",
            interim_response=False,
        )
        brain = SoulBrain(
            config=config_no_interim,
            store=store,
            residents=residents,
            facility=facility,
            preferences=preferences,
        )

        haiku_client = MagicMock()
        mock_haiku_mod.Anthropic.return_value = haiku_client

        plan_json = json.dumps({
            "actions": [{"action_type": "speak", "parameters": {"text": "Done."}}],
            "reasoning": "test",
        })
        sonnet_client = MagicMock()
        sonnet_client.messages.create.return_value = mock_anthropic_response(plan_json)
        mock_sonnet_mod.Anthropic.return_value = sonnet_client

        result = brain.process("I'd like to organize a birthday party for next Tuesday")

        assert result.interim_response is None
        # Haiku should not have been called at all
        haiku_client.messages.create.assert_not_called()

    @patch("soul.cognition.haiku.anthropic")
    def test_preference_uses_haiku(
        self, mock_anthropic_mod, brain, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "I'll remember that you enjoy chamomile tea!"
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("I like chamomile tea")

        assert result.intent.category == IntentCategory.PREFERENCE
        assert result.model_used == brain._config.haiku_model

    @patch("soul.cognition.haiku.anthropic")
    def test_information_uses_haiku(
        self, mock_anthropic_mod, brain, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(
            "Lunch today is tomato soup and grilled cheese."
        )
        mock_anthropic_mod.Anthropic.return_value = mock_client

        result = brain.process("What's for lunch today?")

        assert result.intent.category == IntentCategory.INFORMATION
        assert result.model_used == brain._config.haiku_model

    @patch("soul.cognition.sonnet.anthropic")
    @patch("soul.cognition.haiku.anthropic")
    def test_navigate_request(
        self, mock_haiku_mod, mock_sonnet_mod, brain, mock_anthropic_response
    ):
        haiku_client = MagicMock()
        haiku_client.messages.create.return_value = mock_anthropic_response(
            "Sure, let me take you there."
        )
        mock_haiku_mod.Anthropic.return_value = haiku_client

        plan_json = json.dumps({
            "actions": [
                {"action_type": "speak", "parameters": {"text": "Let's go to the garden!"}},
                {"action_type": "navigate", "parameters": {"destination": "Garden"}},
            ],
            "reasoning": "Navigate to garden.",
        })
        sonnet_client = MagicMock()
        sonnet_client.messages.create.return_value = mock_anthropic_response(plan_json)
        mock_sonnet_mod.Anthropic.return_value = sonnet_client

        result = brain.process("Take me to the garden")

        assert result.intent.category == IntentCategory.REQUEST_NAVIGATE
        assert len(result.action_plan.actions) == 2
        assert result.action_plan.actions[1].action_type == ActionType.NAVIGATE
