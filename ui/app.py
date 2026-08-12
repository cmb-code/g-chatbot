"""
ui/app.py — Gradio Application Builder with Aligned Modern Layout & Recent Chats Sidebar

Layout Specifications Replicated from Architecture:
1. Top Sticky Header with Brand Title, Live Engine Badge, and User Controls.
2. Left Aligned Sidebar featuring 'Recent Chats' history and quick capabilities.
3. Central Chat Canvas with rich markdown responses, EMI cards, and feedback controls.
4. Bottom Floating Capsule Input Bar with language indicator and disclaimer note.
5. Interactive Action Chips below input area for one-click prompts.
"""

import os
import time
import uuid
from collections.abc import AsyncIterator
from typing import Optional, Tuple

import gradio as gr

from agents.automotive_agent import stream_chat_with_autobot
from db.auth import db_create_user, db_authenticate_user
from db.queries import (
    db_create_conversation,
    db_save_chat_message,
    db_get_user_conversations,
    db_get_conversation_messages,
    db_delete_conversation,
)


# ─────────────────────────────────────────────
# Helper Functions: Auth & History UI Handlers
# ─────────────────────────────────────────────

def get_history_choices(user_state: Optional[dict]) -> list[tuple[str, str]]:
    """Fetches past conversations for logged-in user and returns choices for Dropdown/Radio."""
    if not user_state or "id" not in user_state:
        return []
    try:
        convs = db_get_user_conversations(user_state["id"])
        choices = []
        for c in convs:
            title = c.get("title", "Untitled Chat")
            count = c.get("message_count", 0)
            label = f"💬 {title} ({count})"
            choices.append((label, c["session_id"]))
        return choices
    except Exception as e:
        print(f"Error fetching history choices: {e}")
        return []


def on_login(username_or_email: str, password: str):
    """Handles User Login and navigates to Main Chat Application."""
    success, msg, user_dict = db_authenticate_user(username_or_email, password)
    if success and user_dict:
        choices = get_history_choices(user_dict)
        dropdown_update = gr.Dropdown(choices=choices, value=None, interactive=True, allow_custom_value=True)
        status_html = f"<div style='color:#34d399;font-weight:600;font-size:13px;padding:8px;background:rgba(52,211,153,0.1);border-radius:8px;margin-top:8px;'>✅ {msg}</div>"
        user_badge = f"<span style='color:#24262d;font-weight:600;'>{user_dict['username']}</span><br/><span style='color:#7b818c;font-size:11px;'>Free plan</span>"
        return (
            user_dict,                                          # user_state
            status_html,                                        # auth_status
            gr.Column(visible=False),                           # auth_view (hide)
            gr.Column(visible=True),                            # main_view (show)
            dropdown_update,                                    # history_dropdown
            user_badge,                                         # user_badge_md
        )
    else:
        status_html = f"<div style='color:#f87171;font-weight:600;font-size:13px;padding:8px;background:rgba(248,113,113,0.1);border-radius:8px;margin-top:8px;'>❌ {msg}</div>"
        return (
            None,                                               # user_state
            status_html,                                        # auth_status
            gr.Column(visible=True),                            # auth_view (keep visible)
            gr.Column(visible=False),                           # main_view (keep hidden)
            gr.Dropdown(choices=[], value=None, allow_custom_value=True), # history_dropdown
            "<span style='color:#24262d;font-weight:600;'>Guest User</span><br/><span style='color:#7b818c;font-size:11px;'>Free plan</span>",
        )


def on_signup(username: str, email: str, password: str):
    """Handles User Sign Up and navigates to Main Chat Application."""
    success, msg, user_dict = db_create_user(username, email, password)
    if success and user_dict:
        choices = get_history_choices(user_dict)
        dropdown_update = gr.Dropdown(choices=choices, value=None, interactive=True, allow_custom_value=True)
        status_html = f"<div style='color:#34d399;font-weight:600;font-size:13px;padding:8px;background:rgba(52,211,153,0.1);border-radius:8px;margin-top:8px;'>✅ {msg}</div>"
        user_badge = f"<span style='color:#e3e3e3;font-weight:600;'>{user_dict['username']}</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>"
        return (
            user_dict,
            status_html,
            gr.Column(visible=False),                           # auth_view (hide)
            gr.Column(visible=True),                            # main_view (show)
            dropdown_update,
            user_badge,
        )
    else:
        status_html = f"<div style='color:#f87171;font-weight:600;font-size:13px;padding:8px;background:rgba(248,113,113,0.1);border-radius:8px;margin-top:8px;'>❌ {msg}</div>"
        return (
            None,
            status_html,
            gr.Column(visible=True),
            gr.Column(visible=False),
            gr.Dropdown(choices=[], value=None, allow_custom_value=True),
            "<span style='color:#e3e3e3;font-weight:600;'>Guest User</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>",
        )


def on_guest():
    """Allows exploring app as Guest User."""
    return (
        None,                                                   # user_state
        "",                                                     # auth_status
        gr.Column(visible=False),                               # auth_view (hide)
        gr.Column(visible=True),                                # main_view (show)
        gr.Dropdown(choices=[], value=None, interactive=False, allow_custom_value=True), # history_dropdown
        "<span style='color:#24262d;font-weight:600;'>Guest User</span><br/><span style='color:#7b818c;font-size:11px;'>Free plan</span>",
    )


def on_logout():
    """Handles Sign Out and returns to Auth Landing View."""
    return (
        None,                                                   # user_state = None
        None,                                                   # active_session_id = None
        [],                                                     # chatbot = []
        "<div style='color:#94a3b8;font-size:13px;padding:8px;'>Signed out successfully.</div>", # auth_status
        gr.Column(visible=True),                                # auth_view (show)
        gr.Column(visible=False),                               # main_view (hide)
        gr.Dropdown(choices=[], value=None, interactive=False, allow_custom_value=True), # history_dropdown
        "<span style='color:#24262d;font-weight:600;'>Guest User</span><br/><span style='color:#7b818c;font-size:11px;'>Free plan</span>",
        "", "", "", "", ""                                      # clear inputs
    )


def show_login_form():
    """Switch the authentication form without relying on Gradio Tabs internals."""
    return (
        gr.Column(visible=True),
        gr.Column(visible=False),
        gr.Button(elem_classes=["auth-tab", "is-active"]),
        gr.Button(elem_classes=["auth-tab"]),
    )


def show_signup_form():
    """Switch the authentication form without relying on Gradio Tabs internals."""
    return (
        gr.Column(visible=False),
        gr.Column(visible=True),
        gr.Button(elem_classes=["auth-tab"]),
        gr.Button(elem_classes=["auth-tab", "is-active"]),
    )


def on_new_chat(user_state: Optional[dict]) -> Tuple[None, list, str]:
    """Clears chatbot UI and starts a new conversation session."""
    return None, [], "<div style='color:#34d399;font-size:12px;margin-top:4px;'>✨ New chat session started.</div>"


def on_select_history(session_id: str, user_state: Optional[dict]) -> Tuple[str, list, str]:
    """Loads selected past conversation from database into chatbot UI."""
    if not session_id or not user_state or "id" not in user_state:
        return "", [], ""
    try:
        raw_msgs = db_get_conversation_messages(session_id, user_state["id"])
        formatted_history = []
        for m in raw_msgs:
            formatted_history.append({"role": m["role"], "content": m["content"]})
        return session_id, formatted_history, f"<div style='color:#7397cf;font-size:12px;margin-top:4px;'>📂 Loaded chat ({len(formatted_history)} msgs)</div>"
    except Exception as e:
        return "", [], f"<div style='color:#f87171;font-size:12px;margin-top:4px;'>Error loading chat: {e}</div>"


def on_delete_history(session_id: str, user_state: Optional[dict]) -> Tuple[None, list, gr.Dropdown, str]:
    """Deletes selected conversation from database and updates history UI."""
    if not session_id or not user_state or "id" not in user_state:
        return None, [], gr.Dropdown(choices=[], allow_custom_value=True), "<div style='color:#f87171;font-size:12px;margin-top:4px;'>No chat selected to delete.</div>"
    try:
        db_delete_conversation(session_id, user_state["id"])
        choices = get_history_choices(user_state)
        return None, [], gr.Dropdown(choices=choices, value=None, allow_custom_value=True), "<div style='color:#34d399;font-size:12px;margin-top:4px;'>🗑️ Deleted conversation.</div>"
    except Exception as e:
        return session_id, [], gr.Dropdown(choices=[], allow_custom_value=True), f"<div style='color:#f87171;font-size:12px;margin-top:4px;'>Error deleting: {e}</div>"


# ─────────────────────────────────────────────
# Async Main Chat Handler
# ─────────────────────────────────────────────

async def chat(
    user_message: str,
    history: list,
    user_state: Optional[dict],
    active_session_id: Optional[str]
) -> AsyncIterator[Tuple[list, str, Optional[str], gr.Dropdown]]:
    """
    Stream natural-language Markdown into Gradio and persist only completed turns.
    """
    if not user_message.strip():
        choices = get_history_choices(user_state)
        yield history, "", active_session_id, gr.Dropdown(choices=choices, allow_custom_value=True)
        return

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        bot_msg = "**API Key Missing!**\n\nPlease add your `GEMINI_API_KEY` to the `.env` file:\n```\nGEMINI_API_KEY=your_key_here\n```\nGet your key at: https://aistudio.google.com/app/apikey"
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": bot_msg})
        choices = get_history_choices(user_state)
        yield history, "", active_session_id, gr.Dropdown(choices=choices, allow_custom_value=True)
        return

    try:
        session_id = active_session_id
        if user_state and "id" in user_state:
            if not session_id:
                session_id = str(uuid.uuid4())
                title = user_message.strip()[:50]
                db_create_conversation(user_state["id"], session_id, title)

            db_save_chat_message(user_state["id"], session_id, "user", user_message)

        stream_history = list(history)
        stream_history.append({"role": "user", "content": user_message})
        stream_history.append({"role": "assistant", "content": ""})
        choices = get_history_choices(user_state)
        selected_val = session_id if any(c[1] == session_id for c in choices) else None
        dropdown = gr.Dropdown(choices=choices, value=selected_val, allow_custom_value=True)
        output_markdown = ""
        intent_labels: tuple[str, ...] = ()
        elapsed = 0.0
        async for update in stream_chat_with_autobot(
            user_message,
            history,
            user_id=user_state.get("id") if user_state else None,
            session_id=session_id,
        ):
            output_markdown = update.content
            if update.complete:
                intent_labels = update.intents
                elapsed = update.elapsed_seconds
            else:
                stream_history[-1] = {"role": "assistant", "content": output_markdown}
                yield stream_history, "", session_id, dropdown

        formatted = output_markdown + f"\n\n---\n`⚡ Gemini 2.5 Flash Automotive Agent` &nbsp;·&nbsp; `⏱️ {elapsed}s`"
        stream_history[-1] = {"role": "assistant", "content": formatted}

        if user_state and "id" in user_state and session_id:
            db_intent = ",".join(intent_labels) if intent_labels else "unclassified"
            db_save_chat_message(user_state["id"], session_id, "assistant", formatted, intent=db_intent)

        choices = get_history_choices(user_state)
        selected_val = session_id if any(c[1] == session_id for c in choices) else None
        yield stream_history, "", session_id, gr.Dropdown(choices=choices, value=selected_val, allow_custom_value=True)

    except Exception as e:
        print(f"[UI] [ERROR] Chat request failed: {type(e).__name__}: {e}", flush=True)
        error_msg = f"**Error:** {str(e)}\n\nPlease check your API key and try again."
        if "stream_history" in locals():
            stream_history[-1] = {"role": "assistant", "content": error_msg}
        else:
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": error_msg})
            stream_history = history
        choices = get_history_choices(user_state)
        yield stream_history, "", active_session_id, gr.Dropdown(choices=choices, allow_custom_value=True)


# ─────────────────────────────────────────────
# Modern Aligned Dark Theme CSS
# ─────────────────────────────────────────────

PREMIUM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body, .gradio-container {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background: #1b1b1b !important;
    color: #e3e3e3 !important;
    min-height: 100vh;
}

.gradio-container { padding: 0 !important; max-width: 100% !important; }
footer { display: none !important; }

/* ── Authentication: scoped, content-sized two-panel layout ── */
#auth-view {
    min-height: 100vh;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: clamp(24px, 5vh, 48px) 20px !important;
    background: #f8fafc !important;
    color: #0f172a !important;
}

#auth-card {
    width: min(980px, 100%) !important;
    margin: 0 auto !important;
    padding: 0 !important;
    overflow: hidden !important;
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 22px !important;
    box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08) !important;
}

#auth-card > .wrap { padding: 0 !important; }

.auth-layout {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
    align-items: stretch !important;
    width: 100% !important;
    gap: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.auth-layout > .auth-form-pane,
.auth-layout > .auth-promo-pane {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

#auth-card .auth-form-pane {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    padding: 42px 44px !important;
    background: #ffffff !important;
    width: 100% !important;
}
#auth-card .auth-form-pane > .wrap,
#auth-card .auth-form-inner > .wrap {
    width: 100% !important;
    min-height: 0 !important;
}
#auth-card .auth-form-inner {
    width: 100% !important;
    max-width: 420px !important;
    display: flex !important;
    flex-direction: column !important;
    flex: 0 0 auto !important;
}

#auth-card .auth-form-heading { margin: 0 0 26px !important; text-align: left; }
#auth-card .auth-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    margin-bottom: 12px;
    border-radius: 10px;
    background: rgba(93, 128, 182, 0.12);
    color: #5d80b6;
    font-size: 18px;
}
#auth-card .auth-brand {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 32px;
    font-weight: 500;
    letter-spacing: -0.5px;
    line-height: 1.1;
    color: #0f172a;
    margin-bottom: 5px;
}
#auth-card .auth-form-heading p { color: #64748b; font-size: 14px; line-height: 1.5; }

/* Explicit switch buttons avoid Gradio Tabs' generated tab-nav sizing rules. */
#auth-card .auth-tab-switch {
    display: flex !important;
    flex-direction: row !important;
    gap: 12px !important;
    width: 100% !important;
    margin: 0 0 20px !important;
}
#auth-card .auth-tab-switch > * {
    flex: 1 1 0% !important;
    width: 50% !important;
    min-width: 0 !important;
}
#auth-card button.auth-tab {
    width: 100% !important;
    min-height: 42px !important;
    height: 42px !important;
    margin: 0 !important;
    padding: 0 14px !important;
    background: #f8fafc !important;
    border: 1px solid #dbe3ee !important;
    border-radius: 10px !important;
    color: #64748b !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}
#auth-card button.auth-tab.is-active {
    background: #eff5ff !important;
    border-color: #5d80b6 !important;
    color: #0f172a !important;
    font-weight: 600 !important;
}

/* Form fields, status, and guest action all share auth-form-inner's width. */
#auth-card .auth-panel { width: 100% !important; min-height: 0 !important; }
#auth-card .auth-panel > .wrap { padding: 0 !important; min-height: 0 !important; }
#auth-card .auth-field-label {
    display: block;
    margin: 0 0 6px;
    color: #334155;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.01em;
}

#auth-card .auth-input {
    display: block !important;
    margin: 0 0 14px !important;
    padding: 0 !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    width: 100% !important;
}
#auth-card .auth-input:last-of-type { margin-bottom: 0 !important; }

#auth-card .auth-input .input-container {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 46px !important;
    margin-top: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
#auth-card .auth-input .input-container:focus-within {
    border-color: #5d80b6 !important;
    box-shadow: 0 0 0 3px rgba(93, 128, 182, 0.15) !important;
}
#auth-card .auth-input input {
    display: block !important;
    width: 100% !important;
    height: 44px !important;
    min-height: 44px !important;
    margin: 0 !important;
    padding: 0 14px !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    color: #0f172a !important;
    font-size: 14px !important;
    line-height: 44px !important;
    box-shadow: none !important;
}
#auth-card .auth-input input::placeholder { color: #94a3b8 !important; }
#auth-card .auth-input input:focus { outline: 0 !important; box-shadow: none !important; }

#auth-card .gr-textbox,
#auth-card [data-testid="textbox"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

/* Primary CTA Button */
#auth-card .auth-primary,
#auth-card button.auth-primary {
    width: 100% !important;
    min-height: 46px !important;
    height: 46px !important;
    margin-top: 20px !important;
    border: none !important;
    border-radius: 10px !important;
    background: #5d80b6 !important;
    color: #ffffff !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 6px rgba(93, 128, 182, 0.25) !important;
    transition: background 0.15s ease, box-shadow 0.15s ease !important;
}
#auth-card .auth-primary:hover {
    background: #4f71a5 !important;
    box-shadow: 0 4px 12px rgba(93, 128, 182, 0.35) !important;
}

/* Status Notification Component (Hidden when empty) */
#auth-card #auth-status { display: none; min-height: 0 !important; margin: 0 !important; padding: 0 !important; }
#auth-card #auth-status:not(:empty) { display: block !important; }
#auth-card #auth-status > div { margin: 12px 0 0 !important; padding: 10px 14px !important; border-radius: 8px !important; font-size: 13px !important; font-weight: 500 !important; }

/* Guest Section (Secondary CTA inside Form Pane) */
#auth-card .guest-divider {
    margin: 24px 0 10px;
    padding-top: 16px;
    border-top: 1px solid #e2e8f0;
    text-align: center;
    width: 100%;
}
#auth-card .guest-divider span { color: #64748b !important; font-size: 12px; }
#auth-card .guest-button,
#auth-card button.guest-button {
    width: 100% !important;
    margin: 0 !important;
    min-height: 46px !important;
    height: 46px !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #334155 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
}
.guest-button:hover { background: #f8fafc !important; border-color: #94a3b8 !important; }

/* The promo pane is a grid sibling that naturally matches the form pane's height. */
#auth-card .auth-promo-pane {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    padding: 44px !important;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    box-sizing: border-box !important;
}
#auth-card .auth-promo-pane > .wrap { width: 100% !important; }
#auth-card .auth-promo-copy {
    max-width: 320px;
    text-align: center;
}
#auth-card .auth-promo-copy .auth-mark {
    margin-bottom: 20px;
    background: rgba(255, 255, 255, 0.12) !important;
    color: #ffffff !important;
    box-shadow: none;
}
#auth-card .auth-promo-copy h2 {
    color: #ffffff !important;
    font-size: 32px !important;
    font-weight: 600 !important;
    letter-spacing: -0.5px !important;
    line-height: 1.2 !important;
    margin-bottom: 12px !important;
}
#auth-card .auth-promo-copy p {
    margin-top: 0 !important;
    color: #94a3b8 !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}

@media (max-width: 768px) {
    #auth-view { padding: 24px 16px !important; }
    #auth-card { border-radius: 16px !important; width: 100% !important; }
    .auth-layout { grid-template-columns: minmax(0, 1fr) !important; }
    .auth-layout > .auth-form-pane, .auth-layout > .auth-promo-pane { width: 100% !important; }
    #auth-card .auth-form-pane { padding: 32px 20px !important; }
    #auth-card .auth-promo-pane { padding: 32px 20px !important; }
    #auth-card .auth-promo-copy { max-width: 360px; }
    #auth-card .auth-promo-copy .auth-mark { display: none !important; }
    #auth-card .auth-promo-copy h2 { font-size: 24px !important; }
}

/* ── Main Chat App Shell: Sleek Full-Viewport Crisp White Theme ── */
html, body, #root, .gradio-container {
    width: 100% !important;
    min-width: 0 !important;
    min-height: 100% !important;
    margin: 0 !important;
    background: #ffffff !important;
    color: #111827 !important;
}

.gradio-container, .gradio-container > .main, #main-view > .wrap {
    width: 100% !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
    background: #ffffff !important;
}

#main-view {
    --color-accent: #5d80b6;
    --color-accent-soft: rgba(93, 128, 182, 0.12);
    min-height: 100vh !important;
    background: #ffffff !important;
    color: #111827 !important;
}

#main-view > .wrap { padding: 0 !important; }

.top-navbar {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    min-height: 64px !important;
    padding: 0 28px !important;
    background: #ffffff !important;
    border-bottom: 2px solid #111827 !important;
    box-shadow: none !important;
}

.app-workspace {
    min-height: calc(100vh - 64px) !important;
    gap: 0 !important;
    background: #ffffff !important;
}

/* Sidebar */
.sidebar-panel {
    position: sticky !important;
    top: 64px !important;
    height: calc(100vh - 64px) !important;
    min-height: 0 !important;
    padding: 24px 20px !important;
    background: #f9fafb !important;
    border: 0 !important;
    border-right: 2px solid #111827 !important;
    border-radius: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    overflow: hidden auto !important;
}

.sidebar-top-group {
    display: flex !important;
    flex-direction: column !important;
    gap: 14px !important;
    flex-grow: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.sidebar-top-group > * {
    margin-bottom: 0 !important;
    flex-grow: 0 !important;
}

.sidebar-bottom-group {
    margin-top: auto !important;
    padding-top: 20px !important;
    border-top: 1px solid #e5e7eb !important;
    flex-grow: 0 !important;
}

.sidebar-brand {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 24px !important;
    font-weight: 600 !important;
    color: #111827 !important;
    letter-spacing: -0.3px !important;
    margin-bottom: 12px !important;
    padding-left: 2px !important;
}

/* Sidebar Controls */
.sidebar-panel button,
.btn-new-chat,
button.btn-new-chat {
    min-height: 44px !important;
    max-height: 44px !important;
    height: 44px !important;
    padding: 0 16px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    text-align: left !important;
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #111827 !important;
    margin-bottom: 0 !important;
    width: 100% !important;
}

.sidebar-panel button:hover,
.btn-new-chat:hover {
    background: #f0f4fa !important;
    border-color: #5d80b6 !important;
    color: #5d80b6 !important;
}

.sidebar-title, h1, h2, h3, h4, h5, h6 {
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    color: #111827 !important;
    margin: 0 0 8px 0 !important;
}

/* Dropdown Container Overrides */
.history-select,
.history-select > div,
.history-select select,
.history-select input {
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 12px !important;
    color: #111827 !important;
    font-size: 13px !important;
    min-height: 44px !important;
    max-height: 46px !important;
    height: 44px !important;
}

.btn-delete-chat,
button.btn-delete-chat {
    min-height: 42px !important;
    max-height: 42px !important;
    height: 42px !important;
    padding: 0 14px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    background: #ffffff !important;
    border: 1px solid #fca5a5 !important;
    color: #ef4444 !important;
    border-radius: 12px !important;
    margin-top: 0 !important;
    width: 100% !important;
}
.btn-delete-chat:hover {
    background: #fef2f2 !important;
    border-color: #dc2626 !important;
}

.btn-logout,
button.btn-logout {
    min-height: 38px !important;
    max-height: 38px !important;
    height: 38px !important;
    padding: 0 18px !important;
    font-size: 13px !important;
    background: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #374151 !important;
    border-radius: 10px !important;
}
.btn-logout:hover {
    background: #f3f4f6 !important;
    color: #111827 !important;
}

/* Main Chat Area */
.main-chat-area {
    min-height: calc(100vh - 64px) !important;
    padding: 20px clamp(24px, 5vw, 72px) 22px !important;
    background: #ffffff !important;
}

.main-chat-area > .wrap {
    max-width: 1080px !important;
    height: 100% !important;
    margin: 0 auto !important;
    padding: 0 !important;
}

.chat-shell {
    min-height: calc(100vh - 104px) !important;
    background: transparent !important;
    border: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}

/* Chatbot Outer Container (Single Clean Boundary) */
.chatbot-main {
    overflow: hidden !important;
    border: 2px solid #111827 !important;
    border-radius: 16px !important;
    background: #ffffff !important;
    box-shadow: none !important;
    flex: 1 1 auto !important;
}

.chatbot-main > .wrap {
    background: #ffffff !important;
    padding: 20px 24px !important;
    border: 0 !important;
    box-shadow: none !important;
}

/* Explicit Reset for Inner Gradio Containers */
.chatbot-main .wrap,
.chatbot-main .message-wrap,
.chatbot-main .message-row,
.chatbot-main .bubble-wrap,
.chatbot-main .avatar-container,
.chatbot-main .avatar {
    border: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
}

.chatbot-main .message-wrap,
.chatbot-main .message-row {
    margin-bottom: 20px !important;
}

/* Hide Avatar Column & Gap */
.chatbot-main .avatar-container,
.chatbot-main .avatar {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
}

.chatbot-main,
.chatbot-main *:not(button):not(svg):not(path) {
    color: #111827 !important;
}

.chatbot-main button[aria-label*="Copy"],
.chatbot-main button[title*="Copy"],
.chatbot-main button[aria-label*="Share"],
.chatbot-main button[title*="Share"],
.chatbot-main .message-buttons,
.chatbot-main .message-actions {
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Floating Input Bar (Matching 16px Radius) */
.floating-input-bar {
    width: 100% !important;
    max-width: 1080px !important;
    background: #f9fafb !important;
    border: 2px solid #111827 !important;
    border-radius: 16px !important;
    padding: 8px 12px 8px 20px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05) !important;
    margin: 18px auto 0 !important;
}

.floating-input-bar > .wrap {
    padding: 0 !important;
}
.floating-input-bar > .wrap > .row {
    align-items: center !important;
    gap: 10px !important;
}
.floating-input-bar .block { min-width: 0 !important; }

.floating-input-bar textarea {
    background: transparent !important;
    border: none !important;
    color: #111827 !important;
    font-size: 15px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 14px 16px !important;
    resize: none !important;
    caret-color: #5d80b6 !important;
}
.floating-input-bar textarea::placeholder { color: #6b7280 !important; }

/* Action Send Button */
.send-button,
button.send-button {
    background: linear-gradient(135deg, #5d80b6, #30476b) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 0 22px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    min-height: 48px !important;
    max-height: 48px !important;
    box-shadow: 0 4px 14px rgba(93, 128, 182, 0.3) !important;
}
.send-button:hover {
    background: linear-gradient(135deg, #7397cf, #4f71a5) !important;
    transform: translateY(-1px) !important;
}

/* Chatbot Message Bubbles */
.message.user {
    background: #f3f4f6 !important;
    color: #111827 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 16px !important;
    padding: 12px 16px !important;
    max-width: min(760px, 72%) !important;
    margin-left: auto !important;
    margin-right: 0 !important;
    font-size: 15px !important;
}
.message.bot {
    background: transparent !important;
    border: 0 !important;
    color: #111827 !important;
    padding: 14px 0 !important;
    max-width: min(860px, 86%) !important;
    margin-right: auto !important;
    margin-left: 0 !important;
    font-size: 15px !important;
    line-height: 1.7 !important;
}

/* Disclaimer text */
.disclaimer-text {
    text-align: center;
    font-size: 12px;
    color: #6b7280;
    margin-top: 12px;
}

.feature-list {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #e5e7eb;
}
.feature-item {
    display: flex;
    align-items: center;
    min-height: 28px;
    color: #4b5563 !important;
    font-size: 13px;
}
.sync-note {
    color: #6b7280 !important;
    font-size: 12px;
    line-height: 1.4;
}

@media (max-width: 900px) {
    .app-workspace { flex-direction: column !important; }
    .sidebar-panel {
        position: relative !important;
        top: auto !important;
        width: 100% !important;
        height: auto !important;
        border-right: 0 !important;
        border-bottom: 2px solid #111827 !important;
    }
    .main-chat-area { padding: 16px !important; }
    .chatbot-main { border-radius: 16px !important; }
    .message.user,
    .message.bot { max-width: 94% !important; }
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
"""

QUICK_PROMPTS = [
    ("🚗", "Best SUV under Rs.15L for family"),
    ("🔧", "Car vibrates at high speed"),
    ("📅", "Hyundai Creta service at 45000km"),
    ("🏎️", "Honda City vs Creta comparison"),
    ("⚡", "Tata Nexon EV vs Petrol"),
    ("🛢️", "Engine overheating — what to do?"),
    ("🔩", "Brake pad replacement cost"),
    ("🚦", "Tips to improve fuel efficiency"),
]


# ─────────────────────────────────────────────
# Build UI
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Force-light theme: Gradio's Default() theme carries separate
# "_dark" variants for every color variable and auto-activates them
# when the OS/browser prefers dark mode. Overriding classes in CSS
# alone can't reach that — the components read the theme variables
# directly. So we pin every *_dark variable to the same light value
# used by the CSS above, eliminating the dark variant entirely.
# ─────────────────────────────────────────────
FORCED_LIGHT_THEME = gr.themes.Default().set(
    body_background_fill="#ffffff",
    body_background_fill_dark="#ffffff",
    background_fill_primary="#ffffff",
    background_fill_primary_dark="#ffffff",
    background_fill_secondary="#f9fafb",
    background_fill_secondary_dark="#f9fafb",
    block_background_fill="#ffffff",
    block_background_fill_dark="#ffffff",
    body_text_color="#111827",
    body_text_color_dark="#111827",
    block_label_text_color="#111827",
    block_label_text_color_dark="#111827",
    input_background_fill="#ffffff",
    input_background_fill_dark="#ffffff",
    border_color_primary="#e5e7eb",
    border_color_primary_dark="#e5e7eb",
)

# Belt-and-suspenders: also strip any 'dark' class Gradio adds to
# <body>/<html> at load time, in case a future Gradio version still
# toggles a class-based dark mode alongside the theme variables.
FORCE_LIGHT_JS = """
() => {
    document.body.classList.remove('dark');
    document.documentElement.classList.remove('dark');
}
"""


def build_ui():
    with gr.Blocks(
        title="AutoBot — AI Automobile Assistant",
        theme=FORCED_LIGHT_THEME,
        js=FORCE_LIGHT_JS,
    ) as demo:

        # Session States
        user_state = gr.State(value=None)
        active_session_id = gr.State(value=None)

        # ═════════════════════════════════════════════════════════════
        # 1. AUTHENTICATION LANDING VIEW (Visible FIRST on page load)
        # ═════════════════════════════════════════════════════════════
        with gr.Column(visible=True, elem_id="auth-view") as auth_view:
            with gr.Column(elem_id="auth-card"):
                with gr.Row(elem_classes="auth-layout"):
                    with gr.Column(scale=1, min_width=360, elem_classes="auth-form-pane"):
                        with gr.Column(elem_classes="auth-form-inner"):
                            gr.HTML("""
                            <div class="auth-form-heading">
                                <div class="auth-mark">✴️</div>
                                <div class="auth-brand">AutoBot</div>
                                <p>Your AI Automobile Assistant.</p>
                            </div>
                            """)

                            # Explicit buttons + visible panels are more stable than styling
                            # Gradio Tabs' generated tab-nav/tabitem wrappers.
                            with gr.Row(elem_classes="auth-tab-switch"):
                                login_tab_btn = gr.Button("Sign In", elem_classes=["auth-tab", "is-active"])
                                signup_tab_btn = gr.Button("Sign Up", elem_classes=["auth-tab"])

                            with gr.Column(visible=True, elem_classes="auth-panel") as login_form:
                                gr.HTML("<label class='auth-field-label'>Username or Email</label>")
                                login_id_input = gr.Textbox(show_label=False, placeholder="alex or alex@example.com", lines=1, elem_classes="auth-input")
                                gr.HTML("<label class='auth-field-label'>Password</label>")
                                login_pw_input = gr.Textbox(show_label=False, type="password", placeholder="••••••••", lines=1, elem_classes="auth-input")
                                login_btn = gr.Button("Sign In", variant="primary", size="lg", elem_classes="auth-primary")

                            with gr.Column(visible=False, elem_classes="auth-panel") as signup_form:
                                gr.HTML("<label class='auth-field-label'>Username</label>")
                                signup_name_input = gr.Textbox(show_label=False, placeholder="alex", lines=1, elem_classes="auth-input")
                                gr.HTML("<label class='auth-field-label'>Email</label>")
                                signup_email_input = gr.Textbox(show_label=False, placeholder="alex@example.com", lines=1, elem_classes="auth-input")
                                gr.HTML("<label class='auth-field-label'>Password</label>")
                                signup_pw_input = gr.Textbox(show_label=False, type="password", placeholder="At least 6 characters", lines=1, elem_classes="auth-input")
                                signup_btn = gr.Button("Create Account", variant="primary", size="lg", elem_classes="auth-primary")

                            auth_status = gr.HTML("", elem_id="auth-status")

                            gr.HTML("""
                            <div class="guest-divider">
                                <span>Use without saving history</span>
                            </div>
                            """)
                            guest_btn = gr.Button("Continue as Guest", variant="secondary", size="sm", elem_classes="guest-button")

                    with gr.Column(scale=1, min_width=360, elem_classes="auth-promo-pane"):
                        gr.HTML("""
                        <div class="auth-promo-copy">
                            <div class="auth-mark">✴️</div>
                            <h2>AutoBot</h2>
                            <p>Sign in or create an account to save your chat sessions and diagnostic reports.</p>
                        </div>
                        """)

        # ═════════════════════════════════════════════════════════════
        # 2. MAIN APPLICATION VIEW (Replicated Layout Architecture)
        # ═════════════════════════════════════════════════════════════
        with gr.Column(visible=False, elem_id="main-view") as main_view:

            # Top Sticky Header Navigation Bar
            with gr.Row(elem_classes="top-navbar"):
                gr.HTML("""
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-family:'Instrument Serif', Georgia, serif;font-size:24px;color:#111827;font-weight:600;"><span style="color:#5d80b6;">✦</span> AutoBot</span>
                    <span style="font-size:12px;color:#6b7280;font-weight:500;">AI Automobile Assistant</span>
                </div>
                """)
                with gr.Row():
                    user_badge_md = gr.HTML("<span style='color:#111827;font-weight:700;'>Guest User</span>")
                    logout_btn = gr.Button("Sign Out", size="sm", elem_classes="btn-logout")

            with gr.Row(elem_classes="app-workspace"):

                # ── Left Aligned Sidebar Panel (Recent Chats Layout) ──
                with gr.Column(scale=1, min_width=240, elem_classes="sidebar-panel"):
                    with gr.Column(elem_classes="sidebar-top-group"):
                        gr.HTML("<div class='sidebar-title'>Recent Chats</div>")
                        new_chat_btn = gr.Button("+ New Chat", size="sm", elem_classes="btn-new-chat")
                        
                        history_dropdown = gr.Dropdown(
                            label="",
                            choices=[],
                            value=None,
                            interactive=True,
                            allow_custom_value=True,
                            elem_classes="history-select",
                            container=False,
                        )
                        delete_history_btn = gr.Button("Delete Selected Chat", size="sm", elem_classes="btn-delete-chat")
                        history_status = gr.HTML("")

                        gr.HTML("""
                        <div class="feature-list">
                            <div class="sidebar-title">Capabilities</div>
                            <div style="display:flex;flex-direction:column;gap:4px;">
                                <div class="feature-item">Car buying and comparison</div>
                                <div class="feature-item">Issue diagnostics and repair</div>
                                <div class="feature-item">Milestone service planning</div>
                                <div class="feature-item">Loan and EMI calculation</div>
                            </div>
                        </div>
                        """)

                    # Bottom User Profile Footer Card
                    with gr.Column(elem_classes="sidebar-bottom-group"):
                        gr.HTML("<div class='sync-note'>Conversations sync to PostgreSQL when signed in.</div>")

                # ── Main Central Chat Area ──
                with gr.Column(scale=4, elem_classes="main-chat-area"):
                    with gr.Column(elem_classes="chat-shell"):
                        chatbot = gr.Chatbot(
                            value=[],
                            height="calc(100vh - 190px)",
                            elem_classes="chatbot-main",
                            show_label=False,
                            layout="bubble",
                            container=False,
                            placeholder="""
<div style="text-align:center; padding: 18vh 20px 20px 20px;">
    <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 42px; font-weight: 400; color: #111827; letter-spacing: -0.5px; line-height: 1.2;">
        <span style="color: #5d80b6; margin-right: 8px;">✦</span> Good day,
    </div>
    <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 40px; font-weight: 400; color: #374151; margin-top: 6px;">
        What would you like to explore today?
    </div>
</div>
""",
                        )

                        with gr.Column(elem_classes="floating-input-bar"):
                            with gr.Row():
                                msg_input = gr.Textbox(
                                    placeholder="Ask anything about cars",
                                    show_label=False,
                                    lines=1,
                                    max_lines=4,
                                    container=False,
                                    scale=7,
                                )
                                send_btn = gr.Button("Send", variant="primary", elem_classes="send-button", scale=1)

                        gr.HTML("<div class='disclaimer-text'>Responses may be inaccurate. Be sure to verify important details</div>")

        # ── Event Wire Up ───────────────────────────
        login_tab_btn.click(
            fn=show_login_form,
            inputs=[],
            outputs=[login_form, signup_form, login_tab_btn, signup_tab_btn],
        )

        signup_tab_btn.click(
            fn=show_signup_form,
            inputs=[],
            outputs=[login_form, signup_form, login_tab_btn, signup_tab_btn],
        )

        login_btn.click(
            fn=on_login,
            inputs=[login_id_input, login_pw_input],
            outputs=[user_state, auth_status, auth_view, main_view, history_dropdown, user_badge_md],
        )

        signup_btn.click(
            fn=on_signup,
            inputs=[signup_name_input, signup_email_input, signup_pw_input],
            outputs=[user_state, auth_status, auth_view, main_view, history_dropdown, user_badge_md],
        )

        guest_btn.click(
            fn=on_guest,
            inputs=[],
            outputs=[user_state, auth_status, auth_view, main_view, history_dropdown, user_badge_md],
        )

        logout_btn.click(
            fn=on_logout,
            inputs=[],
            outputs=[
                user_state, active_session_id, chatbot, auth_status, auth_view, main_view,
                history_dropdown, user_badge_md, login_id_input, login_pw_input,
                signup_name_input, signup_email_input, signup_pw_input
            ],
        )

        new_chat_btn.click(
            fn=on_new_chat,
            inputs=[user_state],
            outputs=[active_session_id, chatbot, history_status],
        )

        history_dropdown.change(
            fn=on_select_history,
            inputs=[history_dropdown, user_state],
            outputs=[active_session_id, chatbot, history_status],
        )

        delete_history_btn.click(
            fn=on_delete_history,
            inputs=[history_dropdown, user_state],
            outputs=[active_session_id, chatbot, history_dropdown, history_status],
        )

        send_btn.click(
            fn=chat,
            inputs=[msg_input, chatbot, user_state, active_session_id],
            outputs=[chatbot, msg_input, active_session_id, history_dropdown],
        )
        msg_input.submit(
            fn=chat,
            inputs=[msg_input, chatbot, user_state, active_session_id],
            outputs=[chatbot, msg_input, active_session_id, history_dropdown],
        )
    return demo
