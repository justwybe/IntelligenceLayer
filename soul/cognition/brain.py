"""SoulBrain — the main orchestrator for the Wybe Soul System.

Takes an utterance, classifies intent, picks the right model(s),
and returns a complete InteractionResult.

Flow:
  utterance -> classify intent -> pick engine(s) -> generate response/plan -> result

Routing rules:
- Simple intents (greeting, farewell, simple_chat, preference, information):
    Haiku only -> spoken response
- Request intents (request_item, request_navigate):
    Haiku ack + Sonnet plan
- Complex intents (complex_plan, request_help):
    Haiku interim + Sonnet plan
- Emergency:
    Immediate alert_staff action + Haiku acknowledgment
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from soul.cognition.haiku import HaikuEngine
from soul.cognition.prompt import (
    build_acknowledge_prompt,
    build_haiku_prompt,
    build_sonnet_prompt,
)
from soul.cognition.router import classify
from soul.cognition.schemas import (
    Action,
    ActionPlan,
    ActionType,
    Intent,
    IntentCategory,
    InteractionResult,
)
from soul.cognition.sonnet import SonnetEngine

if TYPE_CHECKING:
    from soul.config import SoulConfig
    from soul.memory.facility import FacilityManager
    from soul.memory.preferences import PreferenceManager
    from soul.memory.residents import ResidentManager
    from soul.memory.store import SoulStore
    from soul.memory.tasks import TaskLogger

logger = logging.getLogger(__name__)

# Intents handled purely by Haiku
_HAIKU_ONLY_INTENTS = {
    IntentCategory.GREETING,
    IntentCategory.FAREWELL,
    IntentCategory.SIMPLE_CHAT,
    IntentCategory.PREFERENCE,
    IntentCategory.INFORMATION,
}

# Intents that need Haiku ack + Sonnet plan
_SONNET_INTENTS = {
    IntentCategory.REQUEST_ITEM,
    IntentCategory.REQUEST_NAVIGATE,
    IntentCategory.COMPLEX_PLAN,
    IntentCategory.REQUEST_HELP,
}


class SoulBrain:
    """Main orchestrator: utterance in, InteractionResult out."""

    def __init__(
        self,
        config: SoulConfig,
        store: SoulStore,
        residents: ResidentManager,
        facility: FacilityManager,
        preferences: PreferenceManager,
        task_logger: TaskLogger | None = None,
    ):
        self._config = config
        self._store = store
        self._residents = residents
        self._facility = facility
        self._preferences = preferences
        self._task_logger = task_logger
        self._haiku = HaikuEngine(config)
        self._sonnet = SonnetEngine(config)

    # -- context building --------------------------------------------------

    def _build_resident_context(self, resident_id: str | None) -> str:
        """Build resident context string for prompt injection."""
        if not resident_id:
            return ""
        return self._residents.build_context(resident_id)

    def _build_facility_context(self) -> str:
        """Build facility context string for prompt injection."""
        return self._facility.build_facility_context()

    def _current_time(self) -> str:
        return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    def _build_conversation_summaries(self, resident_id: str | None) -> str:
        """Build a block of recent conversation summaries for the system prompt."""
        if not resident_id or not self._task_logger:
            return ""
        summaries = self._task_logger.recent_summaries(resident_id, limit=5)
        if not summaries:
            return ""
        lines = ["Previous conversations:"]
        for s in summaries:
            lines.append(f"- [{s['started_at']}]: {s['summary']}")
        return "\n".join(lines)

    # -- main entry point --------------------------------------------------

    def process(
        self,
        text: str,
        resident_id: str | None = None,
        history: list[dict] | None = None,
    ) -> InteractionResult:
        """Process a single utterance and return a complete interaction result.

        Args:
            text: The transcribed utterance from the resident.
            resident_id: Optional known resident ID for context injection.
            history: Optional prior messages for multi-turn context.

        Returns:
            InteractionResult with intent, response text, action plan, etc.
        """
        # Step 1: Classify intent
        intent = classify(text)
        logger.info("Intent: %s (confidence=%.2f)", intent.category.value, intent.confidence)

        # Step 2: Route based on intent category
        if intent.category == IntentCategory.EMERGENCY:
            return self._handle_emergency(text, intent, resident_id)
        elif intent.category in _HAIKU_ONLY_INTENTS:
            return self._handle_simple(text, intent, resident_id, history=history)
        elif intent.category in _SONNET_INTENTS:
            return self._handle_complex(text, intent, resident_id)
        else:
            # Fallback — should not happen, but treat as complex
            return self._handle_complex(text, intent, resident_id)

    # -- intent handlers ---------------------------------------------------

    def _handle_emergency(
        self, text: str, intent: Intent, resident_id: str | None
    ) -> InteractionResult:
        """Emergency: immediate alert_staff + Haiku acknowledgment."""
        resident_context = self._build_resident_context(resident_id)

        # Build emergency action plan immediately (no API call needed)
        alert_action = Action(
            action_type=ActionType.ALERT_STAFF,
            parameters={
                "urgency": "critical",
                "reason": f"Emergency detected: {intent.entities.get('trigger', 'unknown')}",
                "resident_id": resident_id or "unknown",
                "utterance": text,
            },
            priority=1,
        )
        speak_action = Action(
            action_type=ActionType.SPEAK,
            parameters={
                "text": "I'm alerting the staff right away. Stay calm, help is on the way."
            },
            priority=1,
        )
        plan = ActionPlan(
            actions=[alert_action, speak_action],
            reasoning="Emergency detected — alerting staff immediately.",
        )

        # Also get a Haiku response for natural communication
        try:
            ack_prompt = build_acknowledge_prompt(
                robot_name=self._config.robot_name,
                facility_name=self._config.facility_name,
                resident_context=resident_context,
            )
            response_text = self._haiku.acknowledge(text, ack_prompt)
        except Exception as exc:
            logger.error("Haiku failed during emergency ack: %s", exc)
            response_text = "I'm getting help right away. Please stay calm."

        return InteractionResult(
            intent=intent,
            response_text=response_text,
            action_plan=plan,
            resident_id=resident_id,
            model_used=self._config.haiku_model,
        )

    def _handle_simple(
        self,
        text: str,
        intent: Intent,
        resident_id: str | None,
        history: list[dict] | None = None,
    ) -> InteractionResult:
        """Simple intents: Haiku-only response, speak-only plan."""
        resident_context = self._build_resident_context(resident_id)
        facility_context = self._build_facility_context()
        conversation_summaries = self._build_conversation_summaries(resident_id)

        system_prompt = build_haiku_prompt(
            robot_name=self._config.robot_name,
            facility_name=self._config.facility_name,
            resident_context=resident_context,
            facility_context=facility_context,
            current_time=self._current_time(),
            conversation_summaries=conversation_summaries,
        )

        response_text = self._haiku.respond(text, system_prompt, history=history)
        plan = ActionPlan.speak_only(response_text)

        return InteractionResult(
            intent=intent,
            response_text=response_text,
            action_plan=plan,
            resident_id=resident_id,
            model_used=self._config.haiku_model,
        )

    def _handle_complex(
        self, text: str, intent: Intent, resident_id: str | None
    ) -> InteractionResult:
        """Complex intents: Haiku interim ack + Sonnet structured plan."""
        resident_context = self._build_resident_context(resident_id)
        facility_context = self._build_facility_context()

        # Quick acknowledgment from Haiku
        interim_response = None
        if self._config.interim_response:
            try:
                ack_prompt = build_acknowledge_prompt(
                    robot_name=self._config.robot_name,
                    facility_name=self._config.facility_name,
                    resident_context=resident_context,
                )
                interim_response = self._haiku.acknowledge(text, ack_prompt)
            except Exception as exc:
                logger.warning("Haiku ack failed, continuing with Sonnet: %s", exc)

        # Structured plan from Sonnet
        sonnet_prompt = build_sonnet_prompt(
            robot_name=self._config.robot_name,
            facility_name=self._config.facility_name,
            resident_context=resident_context,
            facility_context=facility_context,
            current_time=self._current_time(),
        )
        plan = self._sonnet.plan(text, sonnet_prompt)

        # Extract the spoken response from the plan's speak action(s)
        speak_texts = [
            a.parameters.get("text", "")
            for a in plan.actions
            if a.action_type == ActionType.SPEAK
        ]
        response_text = speak_texts[0] if speak_texts else "I'll help you with that."

        return InteractionResult(
            intent=intent,
            response_text=response_text,
            action_plan=plan,
            resident_id=resident_id,
            model_used=self._config.sonnet_model,
            interim_response=interim_response,
        )
