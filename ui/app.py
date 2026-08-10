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
import uuid
from typing import Optional, Tuple

import gradio as gr

from agents.car_agent import chat_with_autobot
from tools.car_tools import calculate_emi, get_all_cars
from ui.formatters import FORMATTERS, format_general
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
        dropdown_update = gr.Dropdown(choices=choices, value=None, interactive=True)
        status_html = f"<div style='color:#34d399;font-weight:600;font-size:13px;padding:8px;background:rgba(52,211,153,0.1);border-radius:8px;margin-top:8px;'>✅ {msg}</div>"
        user_badge = f"<span style='color:#e3e3e3;font-weight:600;'>{user_dict['username']}</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>"
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
            gr.Dropdown(choices=[], value=None),                # history_dropdown
            "<span style='color:#e3e3e3;font-weight:600;'>Guest User</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>",
        )


def on_signup(username: str, email: str, password: str):
    """Handles User Sign Up and navigates to Main Chat Application."""
    success, msg, user_dict = db_create_user(username, email, password)
    if success and user_dict:
        choices = get_history_choices(user_dict)
        dropdown_update = gr.Dropdown(choices=choices, value=None, interactive=True)
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
            gr.Dropdown(choices=[], value=None),
            "<span style='color:#e3e3e3;font-weight:600;'>Guest User</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>",
        )


def on_guest():
    """Allows exploring app as Guest User."""
    return (
        None,                                                   # user_state
        "",                                                     # auth_status
        gr.Column(visible=False),                               # auth_view (hide)
        gr.Column(visible=True),                                # main_view (show)
        gr.Dropdown(choices=[], value=None, interactive=False), # history_dropdown
        "<span style='color:#e3e3e3;font-weight:600;'>Guest User</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>",
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
        gr.Dropdown(choices=[], value=None, interactive=False), # history_dropdown
        "<span style='color:#e3e3e3;font-weight:600;'>Guest User</span><br/><span style='color:#888888;font-size:11px;'>Free plan</span>",
        "", "", "", "", ""                                      # clear inputs
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
        return None, [], gr.Dropdown(choices=[]), "<div style='color:#f87171;font-size:12px;margin-top:4px;'>No chat selected to delete.</div>"
    try:
        db_delete_conversation(session_id, user_state["id"])
        choices = get_history_choices(user_state)
        return None, [], gr.Dropdown(choices=choices, value=None), "<div style='color:#34d399;font-size:12px;margin-top:4px;'>🗑️ Deleted conversation.</div>"
    except Exception as e:
        return session_id, [], gr.Dropdown(choices=[]), f"<div style='color:#f87171;font-size:12px;margin-top:4px;'>Error deleting: {e}</div>"


# ─────────────────────────────────────────────
# Async Main Chat Handler
# ─────────────────────────────────────────────

async def chat(
    user_message: str,
    history: list,
    user_state: Optional[dict],
    active_session_id: Optional[str]
) -> Tuple[list, str, Optional[str], gr.Dropdown]:
    """
    Async chat handler — awaited directly by Gradio's event loop.
    Saves user & assistant messages to PostgreSQL if user is logged in.
    """
    if not user_message.strip():
        choices = get_history_choices(user_state)
        return history, "", active_session_id, gr.Dropdown(choices=choices)

    if not os.getenv("GEMINI_API_KEY"):
        bot_msg = "**API Key Missing!**\n\nPlease add your `GEMINI_API_KEY` to the `.env` file:\n```\nGEMINI_API_KEY=your_key_here\n```\nGet your key at: https://aistudio.google.com/app/apikey"
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": bot_msg})
        choices = get_history_choices(user_state)
        return history, "", active_session_id, gr.Dropdown(choices=choices)

    try:
        session_id = active_session_id
        if user_state and "id" in user_state:
            if not session_id:
                session_id = str(uuid.uuid4())
                title = user_message.strip()[:50]
                db_create_conversation(user_state["id"], session_id, title)

            db_save_chat_message(user_state["id"], session_id, "user", user_message)

        result_obj, intent, is_api_used, engine_name, elapsed = await chat_with_autobot(user_message, history)
        formatter = FORMATTERS.get(intent, format_general)
        formatted = formatter(result_obj)

        if engine_name == "Direct Math Engine":
            meta_badge = f"\n\n---\n`⚡ Direct Math Engine` &nbsp;·&nbsp; `🎯 Intent: {intent}` &nbsp;·&nbsp; `⏱️ {elapsed}s`"
        elif is_api_used:
            meta_badge = f"\n\n---\n`⚡ Live Gemini 2.5 Flash API` &nbsp;·&nbsp; `🎯 Intent: {intent}` &nbsp;·&nbsp; `⏱️ {elapsed}s`"
        else:
            meta_badge = f"\n\n---\n`🟡 Local DB Engine (API Quota Fallback)` &nbsp;·&nbsp; `🎯 Intent: {intent}` &nbsp;·&nbsp; `⏱️ {elapsed}s`"

        formatted += meta_badge

        if user_state and "id" in user_state and session_id:
            db_save_chat_message(user_state["id"], session_id, "assistant", formatted, intent=intent)

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": formatted})

        choices = get_history_choices(user_state)
        return history, "", session_id, gr.Dropdown(choices=choices, value=session_id)

    except Exception as e:
        error_msg = f"**Error:** {str(e)}\n\nPlease check your API key and try again."
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": error_msg})
        choices = get_history_choices(user_state)
        return history, "", active_session_id, gr.Dropdown(choices=choices)


# ─────────────────────────────────────────────
# EMI Calculator Helper & DB Table Helper
# ─────────────────────────────────────────────

def compute_emi(car_name, price, down_pct, rate, months):
    try:
        down = price * (down_pct / 100)
        principal = price - down
        result = calculate_emi(principal, rate, int(months))
        return (
            result["monthly_emi"],
            result["total_interest"],
            result["total_payment"],
            f"Down Payment: Rs.{down:,.0f} | Loan: {result['principal']}",
        )
    except Exception as e:
        return f"Error: {e}", "", "", ""


def get_cars_table():
    cars = get_all_cars()
    rows = []
    for car in cars:
        price = car["price_lakh"]
        mileage = list(car["mileage_kmpl"].values())[0]
        rows.append([
            car["name"], car["brand"], car["segment"],
            f"Rs.{price['min']}L - Rs.{price['max']}L",
            ", ".join(car["fuel_type"]),
            str(mileage),
            str(car["seating"]),
            ", ".join(car["transmission"]),
        ])
    return rows


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

/* ── Authentication: calm, focused Claude-inspired workspace ── */
#auth-view {
    position: relative;
    min-height: 100vh;
    padding: clamp(32px, 7vh, 76px) 24px 48px !important;
    background: transparent !important;
    color: #f3f0eb !important;
    --block-background-fill: transparent;
    --block-border-color: transparent;
    --input-background-fill: #191918;
    --input-border-color: #45423e;
    --color-accent: #7397cf;
    --color-accent-soft: rgba(115, 151, 207, 0.16);
}

#auth-view::before {
    display: none;
}

.auth-mark {
    display: inline-grid;
    width: 38px;
    height: 38px;
    place-items: center;
    margin-bottom: 14px;
    border-radius: 12px;
    background: #5a7eb5;
    color: #fffaf5;
    font-size: 19px;
    box-shadow: 0 5px 14px rgba(51, 82, 126, 0.24);
}

.auth-brand {
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: clamp(38px, 4vw, 48px);
    font-weight: 400;
    letter-spacing: -1.5px;
    line-height: 1;
    color: #f5f1ea;
}

#auth-card {
    position: relative;
    width: min(1080px, 100%) !important;
    min-height: 610px;
    margin: 0 auto !important;
    padding: 0 !important;
    overflow: hidden !important;
    background: #242321 !important;
    border: 1px solid #3a3834 !important;
    border-radius: 28px !important;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.34), 0 2px 5px rgba(0, 0, 0, 0.18) !important;
}

#auth-card > .wrap { padding: 0 !important; }
.auth-layout { min-height: 610px !important; gap: 0 !important; }
.auth-form-pane {
    display: flex !important;
    justify-content: center !important;
    padding: 58px clamp(30px, 6vw, 78px) 38px !important;
    background: #22211f !important;
}
.auth-form-inner { width: 100%; max-width: 385px; }
.auth-form-heading { margin-bottom: 27px; }
.auth-form-heading .auth-brand { margin-bottom: 10px; }
.auth-form-heading p { color: #aaa39a; font-size: 13px; line-height: 1.55; }
.auth-promo-pane {
    position: relative;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 610px;
    overflow: hidden !important;
    padding: 48px !important;
    background: linear-gradient(135deg, #30476b 0%, #202d46 100%) !important;
}
.auth-promo-pane::before {
    content: '';
    position: absolute;
    width: 720px;
    height: 760px;
    right: 42%;
    top: -75px;
    border-radius: 50%;
    background: #22211f;
}
.auth-promo-copy { position: relative; z-index: 1; max-width: 330px; text-align: center; }
.auth-promo-copy .auth-mark { margin-bottom: 22px; background: rgba(255,255,255,.12); box-shadow: none; }
.auth-promo-copy h2 { color: #f6f8fc; font-size: clamp(30px, 3vw, 42px); font-weight: 650; letter-spacing: -.8px; line-height: 1.1; }
.auth-promo-copy p { margin-top: 16px; color: #d8e2f3; font-size: 14px; line-height: 1.65; }

#auth-card .tab-nav {
    display: flex !important;
    justify-content: center !important;
    gap: 10px !important;
    border-bottom: 1px solid #3b3935 !important;
    padding: 0 !important;
}
#auth-card .tab-nav button {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-height: 42px !important;
    width: 116px !important;
    padding: 0 8px !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    color: #98918a !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}
#auth-card .tab-nav button.selected,
#auth-card .tab-nav button[aria-selected="true"] { color: #faf7f1 !important; border-bottom: 2px solid #7397cf !important; }
#auth-card .tabitem { padding: 24px 4px 8px !important; }
#auth-card .auth-tabs .form,
#auth-card .auth-tabs form {
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

/* Each textbox has an explicit class so Gradio's shared form container
   never receives an input border or background. */
#auth-card .auth-input {
    display: block !important;
    margin: 0 0 16px !important;
    padding: 0 !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
#auth-card .auth-input:last-of-type { margin-bottom: 18px !important; }
#auth-card .auth-input label,
#auth-card .auth-input .block-label span {
    color: #d6d0c8 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}

#auth-card .auth-input .input-container {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 46px !important;
    margin-top: 6px !important;
    padding: 0 !important;
    overflow: hidden !important;
    background: #1b1a19 !important;
    border: 1px solid #45423e !important;
    border-radius: 9px !important;
    box-shadow: none !important;
}
#auth-card .auth-input .input-container:focus-within {
    border-color: #7397cf !important;
    box-shadow: 0 0 0 3px rgba(115, 151, 207, 0.16) !important;
}
#auth-card .auth-input input {
    display: block !important;
    width: 100% !important;
    height: 44px !important;
    min-height: 44px !important;
    margin: 0 !important;
    padding: 0 13px !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    color: #f4f0ea !important;
    font-size: 14px !important;
    line-height: 44px !important;
    box-shadow: none !important;
}
#auth-card .auth-input input::placeholder { color: #89837c !important; }
#auth-card .auth-input input:focus { outline: 0 !important; box-shadow: none !important; }
.auth-field-label {
    display: block;
    margin: 0 0 7px;
    color: #d6d0c8;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .01em;
}

/* Reset broad Gradio textbox wrappers: only .form-group controls get a box. */
#auth-card .gr-textbox,
#auth-card [data-testid="textbox"] {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

.auth-primary,
button.auth-primary {
    width: 100% !important;
    min-height: 46px !important;
    margin-top: 8px !important;
    border: 1px solid #6689be !important;
    border-radius: 9px !important;
    background: #5d80b6 !important;
    color: #fffdfa !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 4px rgba(37, 61, 98, 0.28) !important;
    transition: background .18s ease, transform .18s ease, box-shadow .18s ease !important;
}
.auth-primary:hover { background: #4f71a5 !important; transform: translateY(-1px) !important; box-shadow: 0 5px 12px rgba(37, 61, 98, 0.34) !important; }
.auth-primary:active { transform: translateY(0) !important; }

#auth-status { min-height: 0; margin: 0 !important; }
#auth-status > div { margin: 7px 0 0 !important; border-radius: 8px !important; }
.guest-divider { margin: 18px 0 10px; padding-top: 17px; border-top: 1px solid #3b3935; text-align: center; }
.guest-divider span { color: #aaa39a !important; font-size: 12px; }
.guest-button,
button.guest-button { width: 100% !important; margin: 0 0 10px !important; min-height: 40px !important; background: transparent !important; border: 1px solid #4a4742 !important; border-radius: 9px !important; color: #e0dad2 !important; font-size: 13px !important; font-weight: 500 !important; box-shadow: none !important; }
.guest-button:hover { background: #302e2b !important; border-color: #686158 !important; }

@media (max-width: 760px) {
    #auth-view { padding: 32px 14px !important; }
    #auth-view::before { inset: 8px; border-radius: 16px; }
    #auth-card { min-height: 0; border-radius: 18px !important; }
    .auth-layout { min-height: 0 !important; flex-direction: column !important; }
    .auth-form-pane { padding: 38px 24px 30px !important; }
    .auth-promo-pane { min-height: 225px; padding: 38px 26px !important; }
    .auth-promo-pane::before { display: none; }
    .auth-promo-copy { max-width: 390px; }
    .auth-promo-copy .auth-mark { display: none; }
    .auth-promo-copy h2 { font-size: 28px; }
}

/* ── Top Header Navigation Bar ── */
.top-navbar {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    min-height: 58px !important;
    padding: 10px clamp(18px, 3vw, 42px) !important;
    background: #161616 !important;
    border-bottom: 1px solid #262626 !important;
}

#main-view {
    --color-accent: #7397cf;
    --color-accent-soft: rgba(115, 151, 207, 0.16);
}

/* ── Tight Aligned Sidebar Panel ── */
.sidebar-panel {
    background: #161616 !important;
    border: 1px solid #292929 !important;
    border-radius: 14px !important;
    min-height: 540px !important;
    padding: 16px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
}

.sidebar-top-group {
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
    flex-grow: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.sidebar-top-group > * {
    margin-bottom: 8px !important;
    flex-grow: 0 !important;
}

.sidebar-bottom-group {
    margin-top: auto !important;
    padding-top: 12px !important;
    border-top: 1px solid #262626 !important;
    flex-grow: 0 !important;
}

.sidebar-brand {
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-size: 24px !important;
    font-weight: 500 !important;
    color: #f0f0f0 !important;
    letter-spacing: -0.3px !important;
    margin-bottom: 12px !important;
    padding-left: 2px !important;
}

/* Compact Sidebar Buttons */
.sidebar-panel button,
.btn-new-chat,
button.btn-new-chat {
    min-height: 34px !important;
    max-height: 34px !important;
    height: 34px !important;
    padding: 4px 10px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    text-align: left !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: #e3e3e3 !important;
    margin-bottom: 4px !important;
    width: 100% !important;
}

.sidebar-panel button:hover,
.btn-new-chat:hover {
    background: rgba(115, 151, 207, 0.15) !important;
    border-color: #7397cf !important;
    color: #9bb8e4 !important;
}

.sidebar-title {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #888888 !important;
    margin: 0 0 5px 2px !important;
}

/* Dropdown Container Overrides */
.history-select,
.history-select > div,
.history-select select,
.history-select input {
    background: #1e1e1e !important;
    border: 1px solid #2e2e2e !important;
    border-radius: 8px !important;
    color: #e3e3e3 !important;
    font-size: 12px !important;
    min-height: 32px !important;
    max-height: 34px !important;
    height: 32px !important;
}

.btn-delete-chat,
button.btn-delete-chat {
    min-height: 26px !important;
    max-height: 26px !important;
    height: 26px !important;
    padding: 2px 8px !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    background: transparent !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
    color: #f87171 !important;
    border-radius: 6px !important;
    margin-top: 4px !important;
    width: 100% !important;
}
.btn-delete-chat:hover {
    background: rgba(239, 68, 68, 0.15) !important;
    border-color: #ef4444 !important;
    color: #f87171 !important;
}

.btn-logout,
button.btn-logout {
    min-height: 26px !important;
    max-height: 26px !important;
    height: 26px !important;
    padding: 2px 8px !important;
    font-size: 11px !important;
    background: transparent !important;
    border: 1px solid #333333 !important;
    color: #888888 !important;
    border-radius: 6px !important;
}
.btn-logout:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    color: #e3e3e3 !important;
}

/* Main Chat Area */
.main-chat-area {
    padding: 22px clamp(20px, 3vw, 40px) 30px !important;
    background: #1b1b1b !important;
}

.main-chat-area > .wrap { max-width: 1320px !important; margin: 0 auto !important; }
.main-chat-area .tab-nav { margin-bottom: 14px !important; }
.main-chat-area .tab-nav button { min-height: 38px !important; padding: 0 12px !important; }
.chatbot-main {
    overflow: hidden !important;
    border: 1px solid #303139 !important;
    border-radius: 14px !important;
    background: #17181b !important;
}
.chatbot-main > .wrap { background: #17181b !important; }

.pill-row {
    margin-top: 8px !important;
    gap: 6px !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
}

/* Floating Capsule Input Bar */
.floating-input-bar {
    width: 100% !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
    margin: 16px auto 0 !important;
}

.floating-input-bar > .wrap > .row { align-items: center !important; gap: 10px !important; }
.floating-input-bar .block { min-width: 0 !important; }
.floating-input-bar .input-container {
    min-height: 44px !important;
    background: #202126 !important;
    border: 1px solid #3a3d47 !important;
    border-radius: 12px !important;
}
.floating-input-bar textarea {
    min-height: 42px !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 0 !important;
}

.floating-input-bar textarea {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    color: #f0f0f0 !important;
    font-size: 14px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 4px 2px !important;
    resize: none !important;
    caret-color: #7397cf !important;
}
.floating-input-bar textarea::placeholder { color: #888888 !important; }

/* Action Send Button */
.send-button,
button.send-button {
    background: #5d80b6 !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 6px 16px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    min-height: 44px !important;
    max-height: 44px !important;
}
.send-button:hover {
    background: #4f71a5 !important;
    transform: translateY(-1px) !important;
}

/* Suggestion Pill Cards */
.claude-pill-card,
button.claude-pill-card {
    background: #262626 !important;
    border: 1px solid #333333 !important;
    border-radius: 14px !important;
    padding: 5px 14px !important;
    color: #e3e3e3 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    min-height: 30px !important;
    max-height: 32px !important;
}
.claude-pill-card:hover {
    background: #333333 !important;
    border-color: #444444 !important;
    color: #ffffff !important;
}

/* Chatbot Messages */
.message.user {
    background: #2a2a38 !important;
    color: #f0f0f0 !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 12px 18px !important;
    max-width: 75% !important;
    margin-left: auto !important;
    font-size: 14px !important;
}
.message.bot {
    background: transparent !important;
    border: none !important;
    color: #e3e3e3 !important;
    padding: 12px 4px !important;
    max-width: 90% !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
}

/* Disclaimer text */
.disclaimer-text {
    text-align: center;
    font-size: 11px;
    color: #777777;
    margin-top: 6px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #333333; border-radius: 3px; }
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

def build_ui():
    with gr.Blocks(title="AutoBot — AI Automobile Assistant") as demo:

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

                            with gr.Tabs(elem_classes="auth-tabs"):
                                with gr.Tab("Sign In"):
                                    gr.HTML("<label class='auth-field-label'>Username or Email</label>")
                                    login_id_input = gr.Textbox(show_label=False, placeholder="alex or alex@example.com", lines=1, elem_classes="auth-input")
                                    gr.HTML("<label class='auth-field-label'>Password</label>")
                                    login_pw_input = gr.Textbox(show_label=False, type="password", placeholder="••••••••", lines=1, elem_classes="auth-input")
                                    login_btn = gr.Button("Sign In", variant="primary", size="lg", elem_classes="auth-primary")

                                with gr.Tab("Sign Up"):
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
                                <span>Don't want to save history?</span>
                            </div>
                            """)
                            guest_btn = gr.Button("Continue as Guest →", variant="secondary", size="sm", elem_classes="guest-button")

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
                    <span style="font-family:'Instrument Serif', Georgia, serif;font-size:24px;color:#ececec;"><span style="color:#7397cf;">✴️</span> AutoBot</span>
                    <span style="font-size:11px;color:#888888;">AI Automobile Assistant</span>
                </div>
                """)
                with gr.Row():
                    gr.HTML("<span style='background:#262626;border:1px solid #333333;color:#888888;padding:4px 12px;border-radius:16px;font-size:11px;'>Free plan · gemini-2.5-flash</span>")
                    user_badge_md = gr.HTML("<span style='color:#e3e3e3;font-weight:600;'>Guest User</span>")
                    logout_btn = gr.Button("Sign Out 🚪", size="sm", elem_classes="btn-logout")

            with gr.Row():

                # ── Left Aligned Sidebar Panel (Recent Chats Layout) ──
                with gr.Column(scale=1, min_width=240, elem_classes="sidebar-panel"):
                    with gr.Column(elem_classes="sidebar-top-group"):
                        gr.HTML("<div class='sidebar-title'>🕒 Recent Chats</div>")
                        new_chat_btn = gr.Button("+ New Chat 📝", size="sm", elem_classes="btn-new-chat")
                        
                        history_dropdown = gr.Dropdown(
                            label="",
                            choices=[],
                            value=None,
                            interactive=True,
                            elem_classes="history-select",
                            container=False,
                        )
                        delete_history_btn = gr.Button("Delete Selected Chat 🗑️", size="sm", elem_classes="btn-delete-chat")
                        history_status = gr.HTML("")

                        gr.HTML("""
                        <div style="margin-top:14px;padding-top:10px;border-top:1px solid #262626;">
                            <div class="sidebar-title">⚡ Features</div>
                            <div style="display:flex;flex-direction:column;gap:6px;font-size:12px;color:#888888;">
                                <div>🚗 Car Buying & Comparison</div>
                                <div>🔧 Issue Diagnostics & Repair</div>
                                <div>📅 Milestone Service Cost</div>
                                <div>💰 Loan & EMI Calculation</div>
                            </div>
                        </div>
                        """)

                    # Bottom User Profile Footer Card
                    with gr.Column(elem_classes="sidebar-bottom-group"):
                        gr.HTML("<div style='font-size:11px;color:#888888;'>Logged in & synced to PostgreSQL</div>")

                # ── Main Central Chat Area ──
                with gr.Column(scale=4, elem_classes="main-chat-area"):

                    # Main Application Tabs
                    with gr.Tabs(elem_classes="tab-nav"):

                        # ══ Tab 1 — Chat Canvas ═════════════════
                        with gr.Tab("💬 Chat Canvas"):

                            chatbot = gr.Chatbot(
                                value=[],
                                height=520,
                                elem_classes="chatbot-main",
                                show_label=False,
                                layout="bubble",
                                placeholder="""
<div style="text-align:center; padding: 40px 20px 20px 20px;">
    <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 38px; font-weight: 400; color: #ececec; letter-spacing: -0.5px; line-height: 1.2;">
        <span style="color: #7397cf; margin-right: 6px;">✴️</span> Good day,
    </div>
    <div style="font-family: 'Instrument Serif', Georgia, serif; font-size: 36px; font-weight: 400; color: #c4c4c4; margin-top: 4px;">
        What would you like to explore today?
    </div>
</div>
""",
                            )

                            # Floating Pill Input Bar (Replicated Layout from Image)
                            with gr.Column(elem_classes="floating-input-bar"):
                                with gr.Row():
                                    msg_input = gr.Textbox(
                                        placeholder="Ask Anything about Cars...",
                                        show_label=False,
                                        lines=1,
                                        max_lines=4,
                                        container=False,
                                        scale=6,
                                    )
                                    send_btn = gr.Button("Calculate →", variant="primary", elem_classes="send-button", scale=1)

                            gr.HTML("<div class='disclaimer-text'>Responses may be inaccurate. Be sure to verify important details</div>")

                        # ══ Tab 2 — Car Database ════════════════
                        with gr.Tab("🗄️ Car Database"):
                            gr.HTML("""
                            <div style="padding: 24px 0 16px 0;">
                                <h2 style="font-size:20px;font-weight:700;color:#ececec;margin-bottom:4px;">Car Database</h2>
                                <p style="color:#888888;font-size:13px;">All cars available in the AutoBot knowledge base</p>
                            </div>
                            """)
                            gr.Dataframe(
                                value=get_cars_table(),
                                headers=["Car", "Brand", "Segment", "Price", "Fuel", "Mileage (km/l)", "Seats", "Transmission"],
                                interactive=False,
                                wrap=True,
                                elem_classes="dataframe",
                            )

                        # ══ Tab 3 — Guide ═══════════════════════
                        with gr.Tab("📖 Guide"):
                            gr.Markdown("""
## How to Use AutoBot

### User Accounts & History
- **Sign Up / Sign In**: Authenticate on the landing screen to save your chat sessions.
- **Saved Chats**: Your chat history is stored securely in PostgreSQL and listed in the **Recent Chats** sidebar.
- **Auto-Load**: Changing the dropdown selection in the sidebar immediately loads past conversations.
""")

        # ── Event Wire Up ───────────────────────────
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
