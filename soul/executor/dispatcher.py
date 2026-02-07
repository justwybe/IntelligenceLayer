"""Dispatcher — executes an ActionPlan in dependency order.

Walks the action list, respects ``depends_on`` edges, and delegates each
action to the appropriate executor (Speaker, Navigator, Manipulator, or
built-in handlers for WAIT / ALERT_STAFF / REMEMBER / QUERY_MEMORY).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from soul.cognition.schemas import Action, ActionPlan, ActionType

if TYPE_CHECKING:
    from soul.executor.manipulate import Manipulator
    from soul.executor.navigate import Navigator
    from soul.executor.speak import Speaker
    from soul.memory.preferences import PreferenceManager

logger = logging.getLogger(__name__)


@dataclass
class ActionResult:
    """Outcome of executing a single action."""

    action_index: int
    success: bool
    result_text: str = ""
    error: str | None = None


class Dispatcher:
    """Execute an ActionPlan by dispatching each action to its executor."""

    def __init__(
        self,
        speaker: Speaker,
        navigator: Navigator,
        manipulator: Manipulator,
        preferences: PreferenceManager,
        resident_id: str | None = None,
    ):
        self._speaker = speaker
        self._navigator = navigator
        self._manipulator = manipulator
        self._preferences = preferences
        self._resident_id = resident_id

    @property
    def speaker(self) -> Speaker:
        return self._speaker

    # -- public API ------------------------------------------------------------

    def speak(self, text: str) -> None:
        """Convenience: speak text directly via the Speaker."""
        self._speaker.speak(text)

    def execute(self, plan: ActionPlan) -> list[ActionResult]:
        """Execute all actions in *plan* respecting dependency order.

        Returns a list of :class:`ActionResult`, one per action.
        """
        results: list[ActionResult] = []
        completed: dict[int, ActionResult] = {}

        execution_order = self._resolve_order(plan)

        for idx in execution_order:
            action = plan.actions[idx]

            # Check that all dependencies succeeded
            dep_failed = self._check_dependencies(action, completed)
            if dep_failed is not None:
                result = ActionResult(
                    action_index=idx,
                    success=False,
                    error=f"Skipped: dependency {dep_failed} failed",
                )
                results.append(result)
                completed[idx] = result
                continue

            result = self._execute_single(idx, action)
            results.append(result)
            completed[idx] = result

        return results

    # -- dependency resolution -------------------------------------------------

    @staticmethod
    def _resolve_order(plan: ActionPlan) -> list[int]:
        """Topological sort of actions by their ``depends_on`` edges.

        Actions with no dependencies come first. Within the same
        dependency depth, the original list order is preserved.
        """
        n = len(plan.actions)
        if n == 0:
            return []

        # Build in-degree map
        in_degree: dict[int, int] = {i: 0 for i in range(n)}
        dependents: dict[int, list[int]] = {i: [] for i in range(n)}

        for i, action in enumerate(plan.actions):
            for dep in action.depends_on:
                if 0 <= dep < n:
                    in_degree[i] += 1
                    dependents[dep].append(i)

        # Kahn's algorithm — use sorted() to preserve original order among
        # actions with equal readiness.
        queue = sorted(i for i in range(n) if in_degree[i] == 0)
        order: list[int] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for dep in sorted(dependents[current]):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
            queue.sort()

        # If there are cycles, append remaining nodes in index order
        if len(order) < n:
            remaining = sorted(set(range(n)) - set(order))
            logger.warning("Cycle detected in action dependencies — appending remaining: %s", remaining)
            order.extend(remaining)

        return order

    @staticmethod
    def _check_dependencies(
        action: Action, completed: dict[int, ActionResult]
    ) -> int | None:
        """Return the index of the first failed dependency, or None if all ok."""
        for dep in action.depends_on:
            dep_result = completed.get(dep)
            if dep_result is None or not dep_result.success:
                return dep
        return None

    # -- single-action dispatch ------------------------------------------------

    def _execute_single(self, idx: int, action: Action) -> ActionResult:
        """Execute one action and return its result."""
        try:
            handler = self._HANDLERS.get(action.action_type)
            if handler is None:
                return ActionResult(
                    action_index=idx,
                    success=False,
                    error=f"Unknown action type: {action.action_type}",
                )
            return handler(self, idx, action)
        except Exception as exc:
            logger.error("Action %d (%s) raised: %s", idx, action.action_type, exc)
            return ActionResult(action_index=idx, success=False, error=str(exc))

    # -- individual handlers ---------------------------------------------------

    def _handle_speak(self, idx: int, action: Action) -> ActionResult:
        text = action.parameters.get("text", "")
        self._speaker.speak(text)
        return ActionResult(action_index=idx, success=True, result_text=text)

    def _handle_navigate(self, idx: int, action: Action) -> ActionResult:
        destination = action.parameters.get("destination", "")
        ok = self._navigator.navigate(destination)
        return ActionResult(
            action_index=idx,
            success=ok,
            result_text=f"Navigate to {destination}",
            error=None if ok else f"Navigation to {destination} failed",
        )

    def _handle_manipulate(self, idx: int, action: Action) -> ActionResult:
        ok = self._manipulator.execute(action.parameters)
        desc = f"{action.parameters.get('action', '?')} {action.parameters.get('target', '?')}"
        return ActionResult(
            action_index=idx,
            success=ok,
            result_text=desc,
            error=None if ok else f"Manipulation failed: {desc}",
        )

    def _handle_wait(self, idx: int, action: Action) -> ActionResult:
        duration = action.parameters.get("duration", 1.0)
        time.sleep(duration)
        return ActionResult(
            action_index=idx, success=True, result_text=f"Waited {duration}s"
        )

    def _handle_alert_staff(self, idx: int, action: Action) -> ActionResult:
        message = action.parameters.get("message", "Staff alert triggered")
        logger.warning("STAFF ALERT: %s", message)
        self._speaker.speak(f"Alert: {message}")
        return ActionResult(action_index=idx, success=True, result_text=message)

    def _handle_remember(self, idx: int, action: Action) -> ActionResult:
        resident_id = self._resident_id or action.parameters.get("resident_id", "")
        category = action.parameters.get("category", "general")
        key = action.parameters.get("key", "")
        value = action.parameters.get("value", "")

        if not resident_id or not key:
            return ActionResult(
                action_index=idx,
                success=False,
                error="REMEMBER requires resident_id and key",
            )

        pref_id = self._preferences.set(
            resident_id=resident_id,
            category=category,
            key=key,
            value=value,
            source="conversation",
        )
        return ActionResult(
            action_index=idx,
            success=True,
            result_text=f"Stored preference {category}/{key}={value} (id={pref_id})",
        )

    def _handle_query_memory(self, idx: int, action: Action) -> ActionResult:
        resident_id = self._resident_id or action.parameters.get("resident_id", "")
        category = action.parameters.get("category")
        key = action.parameters.get("key")

        if not resident_id:
            return ActionResult(
                action_index=idx,
                success=False,
                error="QUERY_MEMORY requires resident_id",
            )

        if key and category:
            pref = self._preferences.get(resident_id, category, key)
            result_text = f"{category}/{key}={pref['value']}" if pref else f"{category}/{key} not found"
        else:
            prefs = self._preferences.list_for_resident(resident_id, category=category)
            result_text = "; ".join(
                f"{p['category']}/{p['key']}={p['value']}" for p in prefs
            ) or "No preferences found"

        return ActionResult(action_index=idx, success=True, result_text=result_text)

    # -- handler dispatch table ------------------------------------------------

    _HANDLERS = {
        ActionType.SPEAK: _handle_speak,
        ActionType.NAVIGATE: _handle_navigate,
        ActionType.MANIPULATE: _handle_manipulate,
        ActionType.WAIT: _handle_wait,
        ActionType.ALERT_STAFF: _handle_alert_staff,
        ActionType.REMEMBER: _handle_remember,
        ActionType.QUERY_MEMORY: _handle_query_memory,
    }
