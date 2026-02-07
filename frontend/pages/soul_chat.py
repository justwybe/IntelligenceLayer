"""Talk to Wybe — chat interface for the Soul System."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gradio as gr

if TYPE_CHECKING:
    from soul.loop import SoulLoop

logger = logging.getLogger(__name__)

GREETING = "Hello! I'm Wybe. How can I help you today?"


def _resident_choices(soul_loop: SoulLoop | None) -> list[str]:
    if soul_loop is None:
        return []
    try:
        residents = soul_loop.residents.list_all()
        return [f"{r['name']} ({r['id']})" for r in residents]
    except Exception:
        return []


def _model_badge(model_used: str) -> str:
    if "haiku" in model_used.lower():
        return '<span class="soul-badge soul-badge-haiku">haiku</span>'
    if "sonnet" in model_used.lower():
        return '<span class="soul-badge soul-badge-sonnet">sonnet</span>'
    return f'<span class="soul-badge">{model_used}</span>'


def _metadata_html(result: dict) -> str:
    model = _model_badge(result.get("model_used", ""))
    intent = result.get("intent", "?")
    think = result.get("think_time_ms", 0)
    act = result.get("act_time_ms", 0)
    actions = result.get("actions_executed", 0)
    succeeded = result.get("actions_succeeded", 0)
    return (
        f'<div class="soul-metadata">'
        f'<span>Intent: <b>{intent}</b></span>'
        f'<span>{model}</span>'
        f'<span>Think: {think}ms</span>'
        f'<span>Act: {act}ms</span>'
        f'<span>Actions: {succeeded}/{actions}</span>'
        f'</div>'
    )


def create_soul_chat_page(soul_loop: SoulLoop | None) -> dict:
    """Build the Talk to Wybe chat page. Returns dict of components."""

    available = soul_loop is not None

    with gr.Column(visible=True) as page:
        gr.HTML('<div class="page-title">Talk to Wybe</div>')
        if not available:
            gr.HTML(
                '<div style="color:var(--wybe-warning);font-size:13px;margin-bottom:12px">'
                'Soul System unavailable — check ANTHROPIC_API_KEY</div>'
            )

        # -- Controls row --
        with gr.Row():
            with gr.Column(scale=2):
                with gr.Row():
                    resident_dropdown = gr.Dropdown(
                        label="Resident",
                        choices=_resident_choices(soul_loop),
                        value=None,
                        allow_custom_value=False,
                        interactive=available,
                    )
                    refresh_btn = gr.Button("Refresh", size="sm")
            with gr.Column(scale=1):
                convo_status = gr.Textbox(
                    label="Conversation",
                    value="No active conversation",
                    interactive=False,
                )
            with gr.Column(scale=1):
                with gr.Row():
                    start_btn = gr.Button("New Conversation", variant="primary", size="sm", interactive=available)
                    end_btn = gr.Button("End", size="sm", interactive=False)

        # -- Add Resident accordion --
        with gr.Accordion("+ Add Resident", open=False):
            with gr.Row():
                new_name = gr.Textbox(label="Name", placeholder="e.g. Jan de Vries")
                new_room = gr.Textbox(label="Room", placeholder="e.g. 204")
                new_notes = gr.Textbox(label="Notes", placeholder="e.g. Likes classical music")
            add_resident_btn = gr.Button("Add Resident", size="sm", interactive=available)
            add_status = gr.Textbox(label="", interactive=False, visible=False)

        # -- Chat area --
        chatbot = gr.Chatbot(
            value=[{"role": "assistant", "content": GREETING}],
            height=450,
            type="messages",
            show_label=False,
        )

        # -- Input row --
        with gr.Row():
            msg_input = gr.Textbox(
                label="Message",
                placeholder="Type your message to Wybe..." if available else "Soul System unavailable",
                scale=4,
                interactive=available,
                container=False,
            )
            send_btn = gr.Button("Send", variant="primary", scale=1, interactive=available)

        # -- Metadata bar --
        metadata_bar = gr.HTML(
            '<div class="soul-metadata"><span style="color:var(--wybe-text-muted)">Send a message to see response metadata</span></div>'
        )

    # ── State ──
    conversation_id = gr.State(value=None)

    # ── Event handlers ──

    def refresh_residents():
        choices = _resident_choices(soul_loop)
        return gr.update(choices=choices)

    def start_conversation(resident_choice):
        if not soul_loop:
            return "Soul System unavailable", None, gr.update(interactive=False), gr.update(interactive=False)
        rid = None
        if resident_choice:
            rid = resident_choice.rsplit("(", 1)[-1].rstrip(")")
        cid = soul_loop.start_conversation(resident_id=rid)
        name = resident_choice.split(" (")[0] if resident_choice else "Unknown"
        return (
            f"Active — {name}",
            cid,
            gr.update(interactive=False),   # start_btn disabled
            gr.update(interactive=True),    # end_btn enabled
        )

    def end_conversation(cid):
        if soul_loop and cid:
            soul_loop.end_conversation()
        return (
            "No active conversation",
            None,
            gr.update(interactive=True),    # start_btn enabled
            gr.update(interactive=False),   # end_btn disabled
        )

    def send_message(user_msg, chat_history, cid, resident_choice):
        if not soul_loop or not user_msg.strip():
            return chat_history, cid, "", _metadata_html({})

        # Auto-start conversation if none active
        if not cid:
            rid = None
            if resident_choice:
                rid = resident_choice.rsplit("(", 1)[-1].rstrip(")")
            cid = soul_loop.start_conversation(resident_id=rid)

        chat_history = chat_history + [{"role": "user", "content": user_msg}]

        try:
            result = soul_loop.process_text(user_msg)
            chat_history = chat_history + [
                {"role": "assistant", "content": result["response_text"]}
            ]
            meta = _metadata_html(result)
        except Exception as e:
            logger.exception("Soul System error")
            chat_history = chat_history + [
                {"role": "assistant", "content": f"Error: {e}"}
            ]
            meta = '<div class="soul-metadata"><span style="color:var(--wybe-danger)">Error during processing</span></div>'

        return chat_history, cid, "", meta

    def add_resident(name, room, notes):
        if not soul_loop:
            return gr.update(), gr.update(value="Soul System unavailable", visible=True), gr.update()
        if not name.strip():
            return gr.update(), gr.update(value="Name is required", visible=True), gr.update()
        try:
            rid = soul_loop.residents.create(name=name.strip(), room=room.strip() or None, notes=notes.strip() or None)
            choices = _resident_choices(soul_loop)
            return (
                gr.update(choices=choices),
                gr.update(value=f"Added: {name} ({rid})", visible=True),
                gr.update(),
            )
        except Exception as e:
            return gr.update(), gr.update(value=f"Error: {e}", visible=True), gr.update()

    # ── Wire events ──

    refresh_btn.click(refresh_residents, outputs=[resident_dropdown])

    start_btn.click(
        start_conversation,
        inputs=[resident_dropdown],
        outputs=[convo_status, conversation_id, start_btn, end_btn],
    )

    end_btn.click(
        end_conversation,
        inputs=[conversation_id],
        outputs=[convo_status, conversation_id, start_btn, end_btn],
    )

    msg_input.submit(
        send_message,
        inputs=[msg_input, chatbot, conversation_id, resident_dropdown],
        outputs=[chatbot, conversation_id, msg_input, metadata_bar],
    )

    send_btn.click(
        send_message,
        inputs=[msg_input, chatbot, conversation_id, resident_dropdown],
        outputs=[chatbot, conversation_id, msg_input, metadata_bar],
    )

    add_resident_btn.click(
        add_resident,
        inputs=[new_name, new_room, new_notes],
        outputs=[resident_dropdown, add_status, chatbot],
    )

    return {"page": page}
