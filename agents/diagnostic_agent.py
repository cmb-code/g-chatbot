"""
agents/diagnostic_agent.py — Vehicle Diagnostic Agent

Handles the "diagnostic" intent: analyses car symptoms described
by the user and returns a structured diagnostic report.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic_ai import Agent

from models.schemas import DiagnosticReport
from tools.car_tools import get_common_issue_info


# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────
DIAGNOSTIC_SYSTEM_PROMPT = """
You are AutoBot's diagnostic expert. Analyze car symptoms described by the user and provide
a structured diagnostic report.

Be accurate and safety-focused:
- If the issue is Critical or High severity, strongly advise NOT driving the car
- Provide realistic cost estimates in INR for the Indian market
- Consider both authorized service centers and local mechanics
- Provide clear workshop instructions for what to tell the mechanic
- Only suggest DIY fixes for truly simple tasks (e.g., checking fluid levels)

Use the provided database information about common issues when available.
"""

# ─────────────────────────────────────────────
# Singleton Agent
# ─────────────────────────────────────────────
_diagnostic_agent: Optional[Agent[Any, DiagnosticReport]] = None


def get_diagnostic_agent(model: Any) -> Agent[Any, DiagnosticReport]:
    """Return the singleton Diagnostic Agent (created once)."""
    global _diagnostic_agent
    if _diagnostic_agent is None:
        _diagnostic_agent = Agent(
            model=model,
            output_type=DiagnosticReport,
            system_prompt=DIAGNOSTIC_SYSTEM_PROMPT,
            tools=(),  # Data retrieval handled exclusively by query_agent.py (Data Sub-Agent)
        )
        print("🤖 [AGENT] Diagnostic agent initialised (singleton)")
    return _diagnostic_agent


# ─────────────────────────────────────────────
# Fallback (no API / quota exceeded)
# ─────────────────────────────────────────────

def get_fallback_response(user_message: str) -> DiagnosticReport:
    """Local DB fallback when Gemini API is unavailable."""
    issue = get_common_issue_info(user_message)
    if issue:
        return DiagnosticReport(
            symptom_described=user_message,
            possible_causes=issue.get("possible_causes", ["Component wear"]),
            most_likely_cause=issue.get("possible_causes", ["Component wear"])[0],
            severity=issue.get("severity", "Medium"),
            urgency="Schedule mechanic check within a week",
            estimated_repair_cost=f"₹{issue.get('estimated_cost_inr', {}).get('min', 1500)} - ₹{issue.get('estimated_cost_inr', {}).get('max', 5000)}",
            can_drive=True,
            diy_possible=False,
            diy_steps=["Visual check for oil leaks or loose belt tension"],
            workshop_recommendation="Request computerized diagnostic scan and mechanical inspection.",
            parts_that_may_need_replacement=["Filter", "Gasket", "Sensor"]
        )
    return DiagnosticReport(
        symptom_described=user_message,
        possible_causes=["Wheel misalignment or unbalance", "Worn brake rotors or pads", "Ignition misfire"],
        most_likely_cause="Wheel balancing and tire tread uneven wear",
        severity="Medium",
        urgency="Inspect within next 3 to 5 days",
        estimated_repair_cost="₹1,200 - ₹3,800",
        can_drive=True,
        diy_possible=False,
        diy_steps=["Check tire inflation pressure", "Visually inspect tire sidewall and tread depth"],
        workshop_recommendation="Request 4-wheel alignment, balancing, and brake pad thickness check.",
        parts_that_may_need_replacement=["Wheel balancing weights", "Front brake pads"]
    )
