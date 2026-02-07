"""Tests for cognition schemas — Intent, Action, ActionPlan."""

from soul.cognition.schemas import (
    Action,
    ActionPlan,
    ActionType,
    Intent,
    IntentCategory,
    InteractionResult,
)


class TestIntentCategory:
    def test_needs_sonnet(self):
        assert IntentCategory.COMPLEX_PLAN.needs_sonnet is True
        assert IntentCategory.REQUEST_HELP.needs_sonnet is True
        assert IntentCategory.GREETING.needs_sonnet is False
        assert IntentCategory.SIMPLE_CHAT.needs_sonnet is False
        assert IntentCategory.REQUEST_ITEM.needs_sonnet is False


class TestIntent:
    def test_basic_intent(self):
        intent = Intent(
            category=IntentCategory.GREETING,
            raw_text="Hello there!",
        )
        assert intent.category == IntentCategory.GREETING
        assert intent.confidence == 1.0
        assert intent.entities == {}

    def test_intent_with_entities(self):
        intent = Intent(
            category=IntentCategory.REQUEST_ITEM,
            entities={"item": "glasses", "location": "room 204"},
            raw_text="Can you get my glasses from room 204?",
        )
        assert intent.entities["item"] == "glasses"


class TestAction:
    def test_to_dict(self):
        action = Action(
            action_type=ActionType.SPEAK,
            parameters={"text": "Hello!"},
            priority=1,
        )
        d = action.to_dict()
        assert d["action_type"] == "speak"
        assert d["parameters"]["text"] == "Hello!"
        assert d["priority"] == 1
        assert d["depends_on"] == []

    def test_from_dict(self):
        action = Action.from_dict({
            "action_type": "navigate",
            "parameters": {"destination": "room_204"},
            "priority": 3,
            "depends_on": [0],
        })
        assert action.action_type == ActionType.NAVIGATE
        assert action.parameters["destination"] == "room_204"
        assert action.depends_on == [0]

    def test_from_dict_defaults(self):
        action = Action.from_dict({"action_type": "speak"})
        assert action.parameters == {}
        assert action.priority == 5
        assert action.depends_on == []


class TestActionPlan:
    def test_speak_only(self):
        plan = ActionPlan.speak_only("Hello, Martha!")
        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == ActionType.SPEAK
        assert plan.actions[0].parameters["text"] == "Hello, Martha!"
        assert plan.actions[0].priority == 1

    def test_to_dict(self):
        plan = ActionPlan(
            actions=[
                Action(ActionType.SPEAK, {"text": "On my way!"}),
                Action(ActionType.NAVIGATE, {"destination": "room_204"}, depends_on=[0]),
            ],
            reasoning="Resident asked me to come to their room",
        )
        d = plan.to_dict()
        assert len(d["actions"]) == 2
        assert d["actions"][0]["action_type"] == "speak"
        assert d["actions"][1]["depends_on"] == [0]
        assert "room" in d["reasoning"]

    def test_from_dict(self):
        plan = ActionPlan.from_dict({
            "actions": [
                {"action_type": "speak", "parameters": {"text": "Sure!"}},
                {"action_type": "navigate", "parameters": {"destination": "kitchen"}},
                {"action_type": "manipulate", "parameters": {"action": "pick_up", "target": "cup"}, "depends_on": [1]},
            ],
            "reasoning": "Fetch a cup from the kitchen",
        })
        assert len(plan.actions) == 3
        assert plan.actions[2].action_type == ActionType.MANIPULATE
        assert plan.actions[2].depends_on == [1]

    def test_from_dict_empty(self):
        plan = ActionPlan.from_dict({})
        assert plan.actions == []
        assert plan.reasoning == ""


class TestInteractionResult:
    def test_full_result(self):
        result = InteractionResult(
            intent=Intent(IntentCategory.GREETING, raw_text="Hi!"),
            response_text="Hello there! How are you today?",
            action_plan=ActionPlan.speak_only("Hello there! How are you today?"),
            resident_id="abc123",
            model_used="haiku",
        )
        assert result.intent.category == IntentCategory.GREETING
        assert result.model_used == "haiku"
        assert result.interim_response is None
