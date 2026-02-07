"""Data schemas for the cognition layer.

Defines the structured types flowing through the Soul System:
utterance → intent → action plan → interaction result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentCategory(str, Enum):
    """Categories of user intent, from simple to complex."""

    EMERGENCY = "emergency"
    GREETING = "greeting"
    FAREWELL = "farewell"
    SIMPLE_CHAT = "simple_chat"
    REQUEST_ITEM = "request_item"
    REQUEST_NAVIGATE = "request_navigate"
    REQUEST_HELP = "request_help"
    COMPLEX_PLAN = "complex_plan"
    PREFERENCE = "preference"
    INFORMATION = "information"

    @property
    def needs_sonnet(self) -> bool:
        """Whether this intent requires the heavier Sonnet model."""
        return self in (
            IntentCategory.COMPLEX_PLAN,
            IntentCategory.REQUEST_HELP,
        )


@dataclass
class Intent:
    """Classified intent from a user utterance."""

    category: IntentCategory
    confidence: float = 1.0
    entities: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""


class ActionType(str, Enum):
    """Types of actions the robot can execute."""

    SPEAK = "speak"
    NAVIGATE = "navigate"
    MANIPULATE = "manipulate"
    WAIT = "wait"
    ALERT_STAFF = "alert_staff"
    REMEMBER = "remember"
    QUERY_MEMORY = "query_memory"


@dataclass
class Action:
    """A single executable action in an action plan."""

    action_type: ActionType
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1 = highest, 10 = lowest
    depends_on: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "priority": self.priority,
            "depends_on": self.depends_on,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Action:
        return cls(
            action_type=ActionType(data["action_type"]),
            parameters=data.get("parameters", {}),
            priority=data.get("priority", 5),
            depends_on=data.get("depends_on", []),
        )


@dataclass
class ActionPlan:
    """A sequence of actions to execute, with dependency ordering."""

    actions: list[Action] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "actions": [a.to_dict() for a in self.actions],
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ActionPlan:
        return cls(
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            reasoning=data.get("reasoning", ""),
        )

    @classmethod
    def speak_only(cls, text: str) -> ActionPlan:
        """Create a simple plan that just speaks a response."""
        return cls(
            actions=[
                Action(
                    action_type=ActionType.SPEAK,
                    parameters={"text": text},
                    priority=1,
                )
            ]
        )


@dataclass
class InteractionResult:
    """The full result of processing one interaction."""

    intent: Intent
    response_text: str
    action_plan: ActionPlan
    resident_id: str | None = None
    model_used: str = ""
    interim_response: str | None = None  # Quick ack from Haiku for complex requests
