"""
agents/car_agent.py — AutoBot Master Orchestrator with Parallel Multi-Intent Execution

Architecture (Aligned with Pydantic AI):
  - Stage 1: Multi-Intent Router classifies queries into one or multiple tool intents.
  - Stage 2: Delegates DB tool generation & execution to query_agent (Data Sub-Agent).
  - Stage 3: Dispatches pre-retrieved DB context to matching domain sub-agents and executes them
             concurrently in PARALLEL via asyncio.gather().
  - Stage 4: Combines structured sub-agent results into MultiIntentResult and returns to UI.
"""

from __future__ import annotations

import os
import asyncio
import time
from typing import Optional, Any

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel as GeminiModel
from pydantic_ai.providers.google import GoogleProvider

from models.schemas import RoutingDecision, MultiIntentResult
from agents.query_agent import run_query_agent
from agents.recommend_agent import get_recommend_agent, get_fallback_response as recommend_fallback
from agents.diagnostic_agent import get_diagnostic_agent, get_fallback_response as diagnostic_fallback
from agents.service_agent import get_service_agent, get_fallback_response as service_fallback
from agents.emi_agent import handle_emi
from agents.general_agent import handle_general, get_fallback_response as general_fallback


# ─────────────────────────────────────────────
# Master Multi-Intent Routing System Prompt
# ─────────────────────────────────────────────

ORCHESTRATOR_TOOL_ROUTING_PROMPT = """You are AutoBot Master Orchestrator — the routing intelligence for an AI-powered Indian Automobile Assistant.

Your ONLY job is to analyze the user's query and decide which specialist sub-agent tools should handle it.
A user message can contain ONE intent OR MULTIPLE INTENTS (e.g. asking for car recommendations AND loan EMI, or describing a vehicle symptom AND asking about service costs).

## Available Specialist Sub-Agent Tools

| Tool Name            | When to use |
|----------------------|-------------|
| recommend_cars       | User wants car suggestions, comparisons, buying advice, or recommendations based on budget, fuel, segment, or features. |
| diagnose_vehicle     | User describes a car problem, symptom, warning light, noise, vibration, overheating, or mechanical/electrical malfunction. |
| get_service_schedule | User asks about car maintenance, service intervals, oil change, timing belt, scheduled checkups, or service cost. |
| calculate_emi        | User asks about car loan EMI, monthly payments, interest rate, down payment, or loan affordability. |
| answer_general       | All other automobile questions: EV tech, driving tips, fuel efficiency, traffic rules, insurance, car care, spare parts. |

## Decision Rules

1. Identify ALL matching tools that address the user's explicit query parts.
2. If user asks for both recommendations AND EMI → return ["recommend_cars", "calculate_emi"].
3. If user describes a problem AND asks for service schedule → return ["diagnose_vehicle", "get_service_schedule"].
4. ANY symptom, noise, or warning light → include diagnose_vehicle.
5. ANY maintenance or checkup schedule → include get_service_schedule.
6. Loan amount, salary check, or EMI calculation → include calculate_emi.
7. If uncertain → return ["recommend_cars"].

Respond with the list of tool names in `intents` and a brief reason.
"""

TOOL_TO_INTENT = {
    "recommend_cars": "recommend",
    "diagnose_vehicle": "diagnostic",
    "get_service_schedule": "service",
    "calculate_emi": "emi",
    "answer_general": "general",
}

VALID_INTENTS = {"recommend", "diagnostic", "service", "emi", "general"}


# ─────────────────────────────────────────────
# Cached Factories & Semaphores
# ─────────────────────────────────────────────

_cached_model: Any = None
_cached_routing_agent: Optional[Agent[Any, RoutingDecision]] = None
_api_semaphore = asyncio.Semaphore(5)


def get_model() -> Any:
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    _cached_model = GeminiModel("gemini-2.5-flash", provider=GoogleProvider(api_key=api_key))
    return _cached_model


def get_routing_agent() -> Agent[Any, RoutingDecision]:
    """Singleton Pydantic AI routing agent with RoutingDecision output type."""
    global _cached_routing_agent
    if _cached_routing_agent is not None:
        return _cached_routing_agent
    _cached_routing_agent = Agent(
        get_model(),
        output_type=RoutingDecision,
        system_prompt=ORCHESTRATOR_TOOL_ROUTING_PROMPT,
    )
    return _cached_routing_agent


# ─────────────────────────────────────────────
# History Context Builder Helper
# ─────────────────────────────────────────────

def _build_history_context(history: list) -> str:
    """Format last 6 chat turns as context string for specialist agent prompts."""
    if not history:
        return ""
    lines = []
    for msg in history[-6:]:
        if isinstance(msg, (tuple, list)):
            if len(msg) >= 1 and msg[0]:
                lines.append(f"User: {msg[0]}")
            if len(msg) >= 2 and msg[1]:
                lines.append(f"Assistant: {str(msg[1]).rsplit('---', 1)[0].strip()[:400]}")
        elif isinstance(msg, dict):
            role = msg.get("role", "")
            content = str(msg.get("content", ""))
            if isinstance(msg.get("content"), list):
                content = " ".join(
                    str(item.get("text", item)) if isinstance(item, dict) else str(item)
                    for item in msg["content"]
                )
            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Assistant: {content.rsplit('---', 1)[0].strip()[:400]}")
    return "[HISTORY]\n" + "\n".join(lines) + "\n[END HISTORY]\n" if lines else ""


# ─────────────────────────────────────────────
# Stage 1: Intent Classification & Tool Routing LLM Call
# ─────────────────────────────────────────────

async def classify_intents(user_message: str) -> list[str]:
    """Classify user query and return list of intent strings (Single or Multi-Intent)."""
    try:
        async with _api_semaphore:
            res = await get_routing_agent().run(f"USER MESSAGE: {user_message}")
        decision: RoutingDecision = res.output
        resolved_intents = []
        for raw_tool in decision.intents:
            tool_clean = raw_tool.lower().strip()
            if tool_clean in TOOL_TO_INTENT:
                resolved_intents.append(TOOL_TO_INTENT[tool_clean])

        unique_intents = list(dict.fromkeys(resolved_intents))
        if unique_intents:
            print(f"🎯 [PARALLEL MULTI-INTENT ROUTER] Selected Intents: {unique_intents} | Reason: {decision.reason}")
            return unique_intents
    except Exception as e:
        print(f"⚠️ [CAR AGENT] Multi-intent routing fallback due to ({e})")

    # Keyword fallback supporting multi-intent extraction
    msg_lower = user_message.lower()
    fallback_intents = []
    if any(w in msg_lower for w in ["emi", "loan", "down payment", "interest", "finance", "per month"]):
        fallback_intents.append("emi")
    if any(w in msg_lower for w in ["problem", "vibrat", "noise", "smoke", "leak", "warning", "check engine", "shaking"]):
        fallback_intents.append("diagnostic")
    if any(w in msg_lower for w in ["service", "maintenance", "oil change", "timing belt", "km service"]):
        fallback_intents.append("service")
    if any(w in msg_lower for w in ["best", "buy", "recommend", "under", "lakh", "suv", "sedan", "hatchback", "car"]):
        fallback_intents.append("recommend")

    return fallback_intents if fallback_intents else ["general"]


# ─────────────────────────────────────────────
# Stage 3 Helper: Sub-Agent Task Executor
# ─────────────────────────────────────────────

async def _execute_single_subagent(
    intent: str,
    specialist_prompt: str,
    user_message: str,
    query_plan: Any
) -> Any:
    """Executes a single domain sub-agent with proper error fallback handling."""
    try:
        if intent == "recommend":
            agent = get_recommend_agent(get_model())
            async with _api_semaphore:
                res = await agent.run(specialist_prompt)
            return res.output
        elif intent == "diagnostic":
            agent = get_diagnostic_agent(get_model())
            async with _api_semaphore:
                res = await agent.run(specialist_prompt)
            return res.output
        elif intent == "service":
            agent = get_service_agent(get_model())
            async with _api_semaphore:
                res = await agent.run(specialist_prompt)
            return res.output
        elif intent == "emi":
            emi_msg = user_message
            if query_plan and query_plan.emi_price_lakh:
                emi_msg += f" [price={query_plan.emi_price_lakh}L rate={query_plan.emi_interest_rate}% tenure={query_plan.emi_tenure_years}yr]"
            return handle_emi(emi_msg)
        else:
            return await handle_general(user_message, get_model())
    except Exception as e:
        print(f"⚠️ [SUB-AGENT FALLBACK] Sub-agent for '{intent}' failed ({e}) — using fallback")
        if intent == "recommend":
            return recommend_fallback(user_message)
        elif intent == "diagnostic":
            return diagnostic_fallback(user_message)
        elif intent == "service":
            return service_fallback(user_message)
        else:
            return general_fallback(user_message)


# ─────────────────────────────────────────────
# Main Pipeline Orchestrator (Parallel Multi-Intent)
# ─────────────────────────────────────────────

async def chat_with_autobot(user_message: str, history: Optional[list] = None):
    """
    Main Orchestrator Entry Point:
      1. Classifies intent(s) via Pydantic AI Multi-Intent Router (Stage 1)
      2. Routes to query_agent (Data Sub-Agent) to generate LLM DB tool plan & execute DB tools (Stage 2)
      3. Executes matched sub-agents CONCURRENTLY IN PARALLEL via asyncio.gather() (Stage 3)
      4. Returns structured response object (or MultiIntentResult) to presentation layer (Stage 4)

    Returns:
        (pydantic_result_object, intent, is_api_used, engine_name, elapsed_seconds)
    """
    start = time.time()
    print("\n" + "-" * 60)
    print(f"[AutoBot] {time.strftime('%H:%M:%S')} | '{user_message[:70]}'")

    # Stage 1: Classify Intents (Single or Multi-Intent)
    intents = await classify_intents(user_message)

    # Stage 2: Delegate DB Tool Generation & Execution to query_agent (Data Sub-Agent)
    primary_intent = intents[0]
    db_context_str, query_plan = await run_query_agent(
        user_message,
        intent=primary_intent,
        api_semaphore=_api_semaphore,
        model=get_model(),
    )

    history_ctx = _build_history_context(history or [])
    specialist_prompt = "\n\n".join(
        p for p in [history_ctx, db_context_str, f"Question: {user_message}"] if p
    )

    # Stage 3: Run Sub-Agents CONCURRENTLY IN PARALLEL using asyncio.gather()
    is_api_used = True
    engine_name = f"Parallel Gemini 2.5 Flash ({len(intents)} Sub-Agents)" if len(intents) > 1 else "Gemini 2.5 Flash"

    sub_agent_tasks = [
        _execute_single_subagent(intent, specialist_prompt, user_message, query_plan)
        for intent in intents
    ]
    raw_results = await asyncio.gather(*sub_agent_tasks)

    results_map = dict(zip(intents, raw_results))

    if len(intents) == 1:
        result_obj = raw_results[0]
        final_intent = intents[0]
    else:
        result_obj = MultiIntentResult(intents=intents, results=results_map)
        final_intent = "multi_intent"

    elapsed = round(time.time() - start, 2)
    print(f"⚡ [PARALLEL PIPELINE] Executed {len(intents)} sub-agent(s) {intents} concurrently in {elapsed}s | engine={engine_name}")
    print("-" * 60)

    return result_obj, final_intent, is_api_used, engine_name, elapsed
