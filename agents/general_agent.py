"""
agents/general_agent.py — General Q&A Handler

Handles the "general" intent: answers open-ended automotive questions
using a Pydantic AI Agent with GeneralAutoResponse structured output.

Why Pydantic AI?
  - Automatically validates and parses the LLM response into GeneralAutoResponse.
  - No manual JSON parsing or regex cleanup needed.
  - Falls back to a static response if the API fails.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic_ai import Agent
from models.schemas import GeneralAutoResponse


_cached_general_agent: Optional[Agent[Any, GeneralAutoResponse]] = None


# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────
GENERAL_DIRECT_PROMPT = """You are AutoBot, a friendly and knowledgeable automobile assistant for the Indian market.
You can answer questions about:
- Car comparisons and reviews
- Driving tips and traffic rules
- EV technology and future trends
- Insurance and documentation
- Fuel efficiency tips
- Road trips and navigation
- Car care and cleaning tips
- Spare parts and accessories

Always be helpful, accurate, and relevant to the Indian automobile market.
Keep your answer concise and practical.
Suggest 2-3 relevant follow-up questions the user might ask.
Classify your answer into one of: General Info, Car Recommendation, Diagnostics, Service & Maintenance, Finance & Insurance, Parts & Accessories, Driving Tips, Traffic & Laws, EV & Future Tech.
Rate your confidence as High, Medium, or Low.
"""



# ─────────────────────────────────────────────
# Lightweight LLM Handler
# ─────────────────────────────────────────────

def _get_general_agent(model: Any) -> Agent[Any, GeneralAutoResponse]:
    """Singleton Pydantic AI general agent with GeneralAutoResponse output type."""
    global _cached_general_agent
    if _cached_general_agent is not None:
        return _cached_general_agent
    _cached_general_agent = Agent(
        model,
        output_type=GeneralAutoResponse,
        system_prompt=GENERAL_DIRECT_PROMPT,
    )
    return _cached_general_agent


async def handle_general(user_message: str, model: Any) -> GeneralAutoResponse:
    """
    Pydantic AI single-turn agent call for general automotive questions.
    Returns a fully-validated GeneralAutoResponse. Falls back to static response if API fails.
    """
    try:
        res = await _get_general_agent(model).run(f"User question: {user_message}")
        return res.output
    except Exception as e:
        print(f"⚠️ [GENERAL AGENT]: LLM call failed ({e}), using static fallback")
        return get_fallback_response(user_message)


# ─────────────────────────────────────────────
# Fallback
# ─────────────────────────────────────────────

def get_fallback_response(user_message: str) -> GeneralAutoResponse:
    """Static fallback when Gemini API is unavailable."""
    return GeneralAutoResponse(
        answer="AutoBot is your AI automotive assistant for the Indian market. Ask about car recommendations, maintenance schedules, diagnostic checks, or loan EMI calculations!",
        category="General Info",
        follow_up_questions=[
            "Best SUV under Rs.15L for family",
            "Car vibrates at high speed — what to check?",
            "Hyundai Creta 45000km service cost",
        ],
        confidence="High"
    )
