"""
agents/service_agent.py — Service Schedule Agent

Handles the "service" intent: generates a service schedule
based on car model, current mileage, and Indian market norms.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic_ai import Agent

from models.schemas import ServiceScheduleResponse, ServiceItem


# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────
SERVICE_SYSTEM_PROMPT = """
You are AutoBot's service and maintenance expert.
Help users understand their car's service schedule based on current mileage and car model.

Use the standard service intervals provided and customize based on:
- Car model and brand specific intervals
- Current mileage
- Indian driving conditions (add 20% frequency for city stop-go traffic)
- Age of the car if provided

Be practical and cost-conscious. Provide Indian market prices.
"""

# ─────────────────────────────────────────────
# Singleton Agent
# ─────────────────────────────────────────────
_service_agent: Optional[Agent[Any, ServiceScheduleResponse]] = None


def get_service_agent(model: Any) -> Agent[Any, ServiceScheduleResponse]:
    """Return the singleton Service Schedule Agent (created once)."""
    global _service_agent
    if _service_agent is None:
        _service_agent = Agent(
            model=model,
            output_type=ServiceScheduleResponse,
            system_prompt=SERVICE_SYSTEM_PROMPT,
            tools=(),  # Data retrieval handled exclusively by query_agent.py (Data Sub-Agent)
        )
        print("🤖 [AGENT] Service agent initialised (singleton)")
    return _service_agent


# ─────────────────────────────────────────────
# Fallback (no API / quota exceeded)
# ─────────────────────────────────────────────

def get_fallback_response(user_message: str) -> ServiceScheduleResponse:
    """Local DB fallback when Gemini API is unavailable."""
    return ServiceScheduleResponse(
        car_name="Hyundai Creta / Maruti Suzuki / Tata Nexon",
        current_mileage=45000,
        service_items=[
            ServiceItem(item_name="Engine Oil & Oil Filter Replacement", interval_km=10000, last_done_km=35000, due_at_km=45000, status="Due Soon", estimated_cost="₹3,800"),
            ServiceItem(item_name="Air Filter & Cabin AC Filter", interval_km=15000, last_done_km=30000, due_at_km=45000, status="Due Soon", estimated_cost="₹1,200"),
            ServiceItem(item_name="Brake Fluid & Coolant Top-up", interval_km=20000, last_done_km=25000, due_at_km=45000, status="OK", estimated_cost="₹900"),
            ServiceItem(item_name="Spark Plugs Inspection / Cleaning", interval_km=30000, last_done_km=15000, due_at_km=45000, status="OK", estimated_cost="₹1,400"),
        ],
        next_service_due="45,000 km or within 30 days",
        total_estimated_cost="₹7,300 - ₹9,500",
        important_notes=[
            "Use recommended fully synthetic oil (5W-30 or 0W-20) for engine health.",
            "Ask the service advisor for an itemized estimate before approving work.",
        ]
    )
