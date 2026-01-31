"""AI Assistant panel — chat UI with streaming and tool use display."""

from __future__ import annotations

import json
import logging
from typing import Any, Generator

import gradio as gr

from frontend.services.assistant.agent import GREETING, WybeAgent
from frontend.services.assistant.session import ChatSession

logger = logging.getLogger(__name__)


def create_assistant_panel(
    agent: WybeAgent,
) -> dict:
    """Create the assistant panel. Returns dict of components."""

    with gr.Column() as panel:
        gr.HTML(
            '<div class="assistant-header">'
            '<span class="ai-dot"></span>'
            "Wybe Assistant"
            "</div>"
        )

        chatbot = gr.Chatbot(
            height=500,
            value=[{"role": "assistant", "content": GREETING}],
        )

        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Ask me anything about your pipeline...",
                show_label=False,
                scale=4,
                container=False,
            )
            send_btn = gr.Button("Send", variant="primary", scale=0, size="sm")

    def respond(
        user_message: str,
        chat_history: list[dict],
        session_state: dict,
        project: dict,
        current_page: str = "datasets",
    ) -> Generator:
        """Stream responses from the agent."""
        if not user_message.strip():
            yield chat_history, session_state, ""
            return

        # Get or create session
        session_id = session_state.get("session_id")
        session = agent.sessions.get_or_create(session_id)
        session_state["session_id"] = session.session_id

        project_id = project.get("id") if project else None

        # Add user message to chat UI
        chat_history = chat_history + [{"role": "user", "content": user_message}]
        yield chat_history, session_state, ""

        # Check if agent is available
        if not agent.is_available():
            fallback = (
                "I'm currently unavailable — the `ANTHROPIC_API_KEY` environment variable "
                "is not set or the `anthropic` package is not installed.\n\n"
                "You can still use all the UI features directly. Set the API key and "
                "restart to enable the assistant."
            )
            chat_history = chat_history + [{"role": "assistant", "content": fallback}]
            yield chat_history, session_state, ""
            return

        # Stream the response
        assistant_text = ""
        tool_info_parts = []

        try:
            for chunk in agent.chat_stream(user_message, session, project_id, current_page=current_page):
                if chunk["type"] == "text":
                    assistant_text += chunk["content"]
                    # Show current text in chat
                    display = assistant_text
                    if tool_info_parts:
                        display = _format_tool_blocks(tool_info_parts) + "\n\n" + assistant_text
                    updated = chat_history + [{"role": "assistant", "content": display}]
                    yield updated, session_state, ""

                elif chunk["type"] == "tool_call":
                    tool_info_parts.append(
                        f"**Using tool:** `{chunk['name']}`\n"
                        f"```json\n{json.dumps(chunk['input'], indent=2)}\n```"
                    )
                    display = _format_tool_blocks(tool_info_parts)
                    if assistant_text:
                        display = assistant_text + "\n\n" + display
                    updated = chat_history + [{"role": "assistant", "content": display}]
                    yield updated, session_state, ""

                elif chunk["type"] == "tool_result":
                    output_preview = chunk["output"][:500]
                    if len(chunk["output"]) > 500:
                        output_preview += "..."
                    tool_info_parts.append(
                        f"**Result from** `{chunk['name']}`:\n"
                        f"```\n{output_preview}\n```"
                    )
                    display = _format_tool_blocks(tool_info_parts)
                    if assistant_text:
                        display = assistant_text + "\n\n" + display
                    updated = chat_history + [{"role": "assistant", "content": display}]
                    yield updated, session_state, ""

                elif chunk["type"] == "error":
                    error_msg = f"**Error:** {chunk['content']}"
                    updated = chat_history + [{"role": "assistant", "content": error_msg}]
                    yield updated, session_state, ""
                    return

        except Exception as exc:
            logger.exception("Assistant error")
            error_msg = f"**Error:** {exc}"
            updated = chat_history + [{"role": "assistant", "content": error_msg}]
            yield updated, session_state, ""
            return

        # Final update with complete response
        if assistant_text or tool_info_parts:
            final_display = ""
            if tool_info_parts:
                final_display = _format_tool_blocks(tool_info_parts) + "\n\n"
            final_display += assistant_text
            chat_history = chat_history + [{"role": "assistant", "content": final_display}]
        yield chat_history, session_state, ""

    return {
        "panel": panel,
        "chatbot": chatbot,
        "msg_input": msg_input,
        "send_btn": send_btn,
        "respond": respond,
    }


def _format_tool_blocks(tool_parts: list[str]) -> str:
    """Format tool call/result blocks for display."""
    if not tool_parts:
        return ""
    blocks = "\n\n---\n\n".join(tool_parts)
    return f"<details><summary>Tool Activity ({len(tool_parts)} steps)</summary>\n\n{blocks}\n\n</details>"
