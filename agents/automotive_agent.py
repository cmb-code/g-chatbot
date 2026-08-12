"""
agents/automotive_agent.py — Single LLM-Led Pydantic AI Automotive Agent Architecture

Gemini classifies the request, selects zero or more safe tools, reasons over
their results, and produces one validated response. There is no Python intent
classifier, keyword router, fixed tool plan, or generated SQL.
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Optional, Any, Literal

from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    FunctionToolCallEvent,
    PartDeltaEvent,
    PartStartEvent,
    RunContext,
    TextPart,
    TextPartDelta,
)
from pydantic_ai.models.google import GoogleModel as GeminiModel
from pydantic_ai.providers.google import GoogleProvider

from db.fuzzy_queries import fuzzy_engine
from db.queries import db_get_all_issues
from tools.car_tools import (
    get_all_cars,
    filter_cars_by_budget,
    filter_cars_by_fuel,
    filter_cars_by_segment,
    get_car_by_name,
    get_common_issue_info,
    get_service_intervals,
    calculate_emi,
)


@dataclass
class AutoBotDeps:
    """Request-scoped data passed safely to Pydantic AI tools."""
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    history_context: str = ""
    intent_labels: list[str] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AutoBotStreamUpdate:
    """A UI-safe update emitted after the agent graph processes an event."""
    content: str
    intents: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()
    complete: bool = False
    elapsed_seconds: float = 0.0


AUTOMOTIVE_AGENT_PROMPT = """You are AutoBot, one expert AI automobile
assistant for the Indian market. You handle buying, vehicle diagnostics,
maintenance, finance, and general automotive questions in one conversation.

## Your LLM intent-classification job
Before deciding on tools or drafting an answer, classify every explicit user
need into ALL applicable intents:
- buying: recommendations, comparisons, features, budget, purchase decisions
- diagnostics: symptoms, noises, warning lights, faults, drivability, safety
- service: maintenance, service intervals, parts replacement, service cost
- finance: EMI, loan, down payment, affordability, ownership cost
- general: all other automotive questions, including EV, insurance, rules,
  driving, accessories, and out-of-catalogue questions

This classification is your responsibility as the LLM. Never use or imply a
keyword router. As your first action for every request, call
`record_intent_classification` with every applicable intent. A user message can
have multiple intents.

## Tool-use policy
You have safe, read-only tools for local vehicle, issue, service, and finance
data. You decide which tools to use, their order, and their arguments.
1. Use a relevant tool whenever it can provide evidence for a claim.
2. For mixed requests, call every relevant tool; do not retrieve data only for
   the first intent.
3. Treat tool results as the source of truth. Never invent a catalogue model,
   specification, price, service interval, common issue, or calculation.
4. Tools are not a complete market database. For current prices, regulations,
   recalls, incentives, insurance terms, launches, or availability not returned
   by a tool, say live verified research is not configured and do not present
   your model memory as a current fact.
5. Never generate SQL, ask for credentials, or claim access to data a tool did
   not return.

## Automotive safety policy
Your diagnostic advice is triage, not a confirmed repair diagnosis. If the user
describes brake or steering loss, smoke/fire, fuel leak, severe overheating,
loss of control, or a critical warning, lead with a clear 'do not drive' and
professional-assistance recommendation. Do not provide risky repair steps.
Ask focused questions when the make, model, year, fuel type, warning code, or
driving conditions are needed for a reliable answer.

## Finance policy
Use the EMI calculator tool for every numeric EMI result. Do not do EMI math
yourself. State all material assumptions, including price basis, down payment,
rate, and tenure. A catalogue price is a base price, not an on-road quote.

## Response policy
After you have finished any useful tool calls, write one practical, concise,
natural-language Markdown response for the user. Lead with safety where
relevant. State evidence, material assumptions, focused follow-up questions
only when they improve the answer, and honest uncertainty in normal language.
Do not output JSON, Pydantic field names, internal classifications, tool names,
or hidden reasoning."""

_cached_model: Optional[GeminiModel] = None
_cached_agent: Optional[Agent[AutoBotDeps, str]] = None


def get_model() -> GeminiModel:
    """Create the shared Gemini model after checking for configured credentials."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    _cached_model = GeminiModel("gemini-2.5-flash", provider=GoogleProvider(api_key=api_key))
    return _cached_model


def get_automotive_agent() -> Agent[AutoBotDeps, str]:
    """Return one reusable agent with all safe automotive evidence tools."""
    global _cached_agent
    if _cached_agent is not None:
        return _cached_agent

    agent = Agent[AutoBotDeps, str](
        get_model(),
        name="autobot",
        deps_type=AutoBotDeps,
        output_type=str,
        system_prompt=AUTOMOTIVE_AGENT_PROMPT,
        retries=2,
    )

    @agent.tool
    def record_intent_classification(
        ctx: RunContext[AutoBotDeps],
        intents: list[Literal["buying", "diagnostics", "service", "finance", "general"]],
    ) -> str:
        """Record the LLM's intent classification before selecting evidence tools."""
        ctx.deps.intent_labels = list(dict.fromkeys(intents))
        labels = " && ".join(ctx.deps.intent_labels)
        print(f"[AUTOBOT] LLM intent classified: {labels}", flush=True)
        return f"Intent classification recorded: {labels}"

    @agent.tool
    def search_catalog(ctx: RunContext[AutoBotDeps]) -> list[dict[str, Any]]:
        """Return all verified vehicles in the local catalogue."""
        return get_all_cars()

    @agent.tool
    def search_catalog_by_budget(ctx: RunContext[AutoBotDeps], max_budget_lakh: float) -> list[dict[str, Any]]:
        """Return vehicles whose listed base price starts within a budget in lakhs."""
        return filter_cars_by_budget(max_budget_lakh)

    @agent.tool
    def search_catalog_by_fuel(ctx: RunContext[AutoBotDeps], fuel_type: str) -> list[dict[str, Any]]:
        """Return vehicles supporting a requested fuel type."""
        return filter_cars_by_fuel(fuel_type)

    @agent.tool
    def search_catalog_by_segment(ctx: RunContext[AutoBotDeps], segment: str) -> list[dict[str, Any]]:
        """Return vehicles matching a segment such as SUV, Sedan, or Hatchback."""
        return filter_cars_by_segment(segment)

    @agent.tool
    def get_vehicle(ctx: RunContext[AutoBotDeps], name: str) -> Optional[dict[str, Any]]:
        """Look up one catalogue vehicle by a partial model name."""
        return get_car_by_name(name)

    @agent.tool
    def search_known_issue(ctx: RunContext[AutoBotDeps], symptom_or_issue: str) -> Optional[dict[str, Any]]:
        """Search verified common-issue records using a symptom or issue phrase."""
        exact_or_partial = get_common_issue_info(symptom_or_issue)
        if exact_or_partial:
            return exact_or_partial
        all_issues = db_get_all_issues()
        return fuzzy_engine.search_issue(symptom_or_issue, all_issues)

    @agent.tool
    def get_standard_service_intervals(ctx: RunContext[AutoBotDeps]) -> dict[str, Any]:
        """Return locally verified generic service intervals and estimated costs."""
        return get_service_intervals()

    @agent.tool
    def calculate_loan_emi(
        ctx: RunContext[AutoBotDeps],
        principal_inr: float,
        annual_interest_rate: float,
        tenure_months: int,
    ) -> dict[str, Any]:
        """Calculate EMI for a positive INR principal, annual rate, and positive tenure."""
        if principal_inr <= 0 or tenure_months <= 0 or annual_interest_rate < 0:
            return {"error": "principal and tenure must be positive; interest rate cannot be negative"}
        return calculate_emi(principal_inr, annual_interest_rate, tenure_months)

    _cached_agent = agent
    return _cached_agent


def _history_context(history: list[Any]) -> str:
    """Pass a bounded text representation of prior conversation turns to Gemini."""
    lines = []
    for message in (history or [])[-6:]:
        if isinstance(message, dict):
            role = message.get("role")
            content = str(message.get("content", ""))
            if role in ("user", "assistant") and content:
                lines.append(f"{role.title()}: {content[:500]}")
    return "\n".join(lines)


async def chat_with_autobot(
    user_message: str,
    history: Optional[list[Any]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> tuple[str, str, bool, str, float]:
    """Run the one-agent automotive workflow and preserve the UI return contract."""
    output = ""
    intents: tuple[str, ...] = ()
    elapsed = 0.0
    async for update in stream_chat_with_autobot(user_message, history, user_id, session_id):
        output = update.content
        if update.complete:
            intents = update.intents
            elapsed = update.elapsed_seconds
    intent = ",".join(intents) if intents else "unclassified"
    return output, intent, True, "Gemini 2.5 Flash Automotive Agent", elapsed


async def stream_chat_with_autobot(
    user_message: str,
    history: Optional[list[Any]] = None,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
) -> AsyncIterator[AutoBotStreamUpdate]:
    """Stream the one agent's final natural-language response to the UI.

    The LLM can complete model-selected tool calls before text begins. Each
    value afterwards is the complete generated response so far, ready for
    Gradio's Chatbot component.
    """
    history_context = _history_context(history) if history else ""
    deps = AutoBotDeps(user_id=user_id, session_id=session_id, history_context=history_context)
    prompt = (
        f"[CONVERSATION CONTEXT]\n{history_context if history_context else '(none)'}\n[END CONTEXT]\n\n"
        f"USER: {user_message}"
    )

    started = time.monotonic()
    text_parts: dict[int, str] = {}
    final_output = ""

    def current_text() -> str:
        return "".join(text_parts[index] for index in sorted(text_parts))

    try:
        async with get_automotive_agent().run_stream_events(prompt, deps=deps) as events:
            async for event in events:
                if isinstance(event, FunctionToolCallEvent):
                    tool_name = event.part.tool_name
                    deps.tool_calls.append(tool_name)
                    print(f"[AUTOBOT] LLM selected tool: {tool_name}", flush=True)
                elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                    text_parts[event.index] = event.part.content
                    yield AutoBotStreamUpdate(content=current_text())
                elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                    text_parts[event.index] = text_parts.get(event.index, "") + event.delta.content_delta
                    yield AutoBotStreamUpdate(content=current_text())
                elif isinstance(event, AgentRunResultEvent):
                    final_output = event.result.output
    except Exception as exc:
        print(f"[AUTOBOT] ERROR: {type(exc).__name__}: {exc}", flush=True)
        if "429" in str(exc) or "quota" in str(exc).lower() or "RESOURCE_EXHAUSTED" in str(exc):
            quota_msg = (
                "⚠️ **Gemini API Rate Limit / Daily Quota Reached**\n\n"
                "The free-tier Gemini API request limit (`20 requests/day` for gemini-2.5-flash) has been temporarily exhausted.\n\n"
                "**How to fix:**\n"
                "1. Please wait **20 to 60 seconds** and try your request again.\n"
                "2. Or add a fresh `GEMINI_API_KEY` in your `.env` file.\n"
            )
            yield AutoBotStreamUpdate(
                content=quota_msg,
                intents=tuple(deps.intent_labels) if deps.intent_labels else ("rate_limit",),
                tool_calls=tuple(deps.tool_calls),
                complete=True,
                elapsed_seconds=round(time.monotonic() - started, 2),
            )
            return
        raise

    elapsed = round(time.monotonic() - started, 2)
    final_text = final_output or current_text()
    if not deps.intent_labels:
        print("[AUTOBOT] WARNING: LLM completed without intent classification", flush=True)
    yield AutoBotStreamUpdate(
        content=final_text,
        intents=tuple(deps.intent_labels),
        tool_calls=tuple(deps.tool_calls),
        complete=True,
        elapsed_seconds=elapsed,
    )
