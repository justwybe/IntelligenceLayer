"""WybeAgent — ReAct loop with Anthropic API for the Wybe Studio assistant."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Generator

from frontend.services.assistant.context import build_project_context
from frontend.services.assistant.prompt import build_system_prompt
from frontend.services.assistant.session import ChatSession, SessionManager
from frontend.services.assistant.tools.base import ToolContext, ToolRegistry
from frontend.services.assistant.tools.data_tools import DATA_TOOLS
from frontend.services.assistant.tools.deploy_tools import DEPLOY_TOOLS
from frontend.services.assistant.tools.eval_tools import EVAL_TOOLS
from frontend.services.assistant.tools.system_tools import SYSTEM_TOOLS
from frontend.services.assistant.tools.train_tools import TRAIN_TOOLS
from frontend.services.assistant.tools.workspace_tools import WORKSPACE_TOOLS

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10

# Greeting message when the assistant first loads
GREETING = (
    "Hey — I'm your Wybe assistant. I know the full GR00T N1.6 pipeline inside and out: "
    "**data → training → simulation → deployment**.\n\n"
    "I can help you with anything:\n"
    '- **"Walk me through the whole workflow"** — I\'ll guide you step by step\n'
    '- **"Import my dataset"** — I\'ll handle the LeRobot v2 format\n'
    '- **"What learning rate should I use?"** — I\'ll explain the trade-offs\n'
    '- **"Train on my data"** — I\'ll configure and launch it\n'
    '- **"Evaluate my model"** — open-loop eval, sim rollouts, benchmarks\n'
    '- **"Deploy to my robot"** — policy server, ONNX, TensorRT\n\n'
    "What are you working on?"
)


class WybeAgent:
    """AI assistant agent with tool use for Wybe Studio."""

    def __init__(
        self,
        store: Any,
        task_runner: Any,
        server_manager: Any,
        project_root: str,
        model: str | None = None,
    ):
        self.store = store
        self.task_runner = task_runner
        self.server_manager = server_manager
        self.project_root = project_root
        self.model = model or os.environ.get("WYBE_ASSISTANT_MODEL", "claude-sonnet-4-20250514")
        self.sessions = SessionManager()
        self.tools = ToolRegistry()
        self._register_all_tools()
        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic()
            except ImportError:
                logger.warning("anthropic package not installed — assistant unavailable")
                return None
            except Exception as exc:
                logger.warning("Failed to init Anthropic client: %s", exc)
                return None
        return self._client

    def _register_all_tools(self) -> None:
        for tool in WORKSPACE_TOOLS + SYSTEM_TOOLS + DATA_TOOLS + TRAIN_TOOLS + EVAL_TOOLS + DEPLOY_TOOLS:
            self.tools.register(tool)

    def _build_context(self, project_id: str | None) -> ToolContext:
        return ToolContext(
            store=self.store,
            task_runner=self.task_runner,
            server_manager=self.server_manager,
            project_root=self.project_root,
            current_project_id=project_id,
        )

    def is_available(self) -> bool:
        """Check if the assistant is available (API key set and package installed)."""
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except ImportError:
            return False

    def chat(
        self,
        user_message: str,
        session: ChatSession,
        project_id: str | None = None,
        current_page: str = "datasets",
    ) -> str:
        """Synchronous chat — sends message, runs tool loop, returns final text."""
        result_parts = []
        for chunk in self.chat_stream(user_message, session, project_id, current_page=current_page):
            if chunk["type"] == "text":
                result_parts.append(chunk["content"])
        return "".join(result_parts)

    def chat_stream(
        self,
        user_message: str,
        session: ChatSession,
        project_id: str | None = None,
        current_page: str = "datasets",
    ) -> Generator[dict, None, None]:
        """Streaming chat with tool use.

        Yields dicts:
          {"type": "text", "content": "..."}
          {"type": "tool_call", "name": "...", "input": {...}}
          {"type": "tool_result", "name": "...", "output": "..."}
          {"type": "error", "content": "..."}
        """
        client = self._get_client()
        if client is None:
            yield {"type": "error", "content": "Assistant unavailable — check ANTHROPIC_API_KEY and anthropic package."}
            return

        # Add user message to session
        session.add_user_message(user_message)

        # Build system prompt with current context
        project_context = build_project_context(self.store, self.server_manager, project_id, current_page=current_page)
        system_prompt = build_system_prompt(project_context)

        tool_context = self._build_context(project_id)
        api_tools = self.tools.to_api_format()

        for _iteration in range(MAX_TOOL_ITERATIONS):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=api_tools,
                    messages=session.get_api_messages(),
                )
            except Exception as exc:
                error_msg = f"API error: {exc}"
                logger.exception("Anthropic API call failed")
                yield {"type": "error", "content": error_msg}
                session.add_assistant_message(error_msg)
                return

            # Process response content blocks
            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                    yield {"type": "text", "content": block.text}
                elif block.type == "tool_use":
                    tool_uses.append(block)
                    yield {"type": "tool_call", "name": block.name, "input": block.input}

            # If no tool use, we're done
            if not tool_uses:
                full_text = "".join(text_parts)
                session.add_assistant_message(full_text)
                return

            # Record assistant response with tool uses
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            session.messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and add results
            tool_results = []
            for tool_use in tool_uses:
                result = self.tools.execute(tool_use.name, tool_use.input, tool_context)
                yield {
                    "type": "tool_result",
                    "name": tool_use.name,
                    "output": result.output,
                    "is_error": result.is_error,
                }
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result.output,
                    **({"is_error": True} if result.is_error else {}),
                })

            session.messages.append({"role": "user", "content": tool_results})

            # If stop_reason is end_turn, we're done even with tools
            if response.stop_reason == "end_turn":
                return

        # Max iterations reached
        yield {"type": "text", "content": "\n\n*[Reached maximum tool iterations]*"}
