"""
agents/recommend_agent.py — Car Recommendation Agent

Handles the "recommend" intent: finds and ranks cars based on
user requirements (budget, fuel, segment, seating, features).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic_ai import Agent

from models.schemas import CarRecommendationResponse, CarSpec
from tools.car_tools import get_all_cars


# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────
RECOMMEND_SYSTEM_PROMPT = """
You are AutoBot, an expert automobile advisor specializing in the Indian car market.
Your role is to recommend the best cars based on user requirements.

Use the provided car database information to make data-driven recommendations.
Always consider:
- Budget constraints
- Family size and seating needs
- Fuel type preference (EV, Petrol, Diesel, CNG, Hybrid)
- Usage pattern (city driving, highway, off-road)
- Transmission preference
- Features required

Return EXACTLY 3 car recommendations maximum, with honest pros and cons.
Give a match_score (0-100) based on how well each car matches the user's requirements.
Be specific about prices in INR (lakhs).
Always include practical buying tips relevant to the Indian market.
"""

# ─────────────────────────────────────────────
# Singleton Agent
# ─────────────────────────────────────────────
_recommend_agent: Optional[Agent[Any, CarRecommendationResponse]] = None


def get_recommend_agent(model: Any) -> Agent[Any, CarRecommendationResponse]:
    """Return the singleton Car Recommendation Agent (created once)."""
    global _recommend_agent
    if _recommend_agent is None:
        _recommend_agent = Agent(
            model=model,
            output_type=CarRecommendationResponse,
            system_prompt=RECOMMEND_SYSTEM_PROMPT,
            tools=(),  # Data retrieval handled exclusively by query_agent.py (Data Sub-Agent)
        )
        print("🤖 [AGENT] Recommendation agent initialised (singleton)")
    return _recommend_agent


# ─────────────────────────────────────────────
# Fallback (no API / quota exceeded)
# ─────────────────────────────────────────────

def get_fallback_response(user_message: str) -> CarRecommendationResponse:
    """Local DB fallback when Gemini API is unavailable."""
    all_cars = get_all_cars()
    msg_lower = user_message.lower()

    # Brand query handling
    if any(w in msg_lower for w in ["brand", "brands", "all cars", "list cars", "every car", "available cars"]):
        recs = []
        scores = [98.0, 95.0, 93.0, 90.0, 88.0, 86.0, 84.0]
        for idx, c in enumerate(all_cars):
            m = c.get("mileage_kmpl", 18.0)
            mileage_val = float(list(m.values())[0]) if isinstance(m, dict) and m else float(m) if m else 18.0
            recs.append(CarSpec(
                car_name=c["name"],
                brand=c["brand"],
                price_range=f"₹{c['price_lakh']['min']}L - ₹{c['price_lakh']['max']}L",
                fuel_type=c["fuel_type"][0] if isinstance(c["fuel_type"], list) else c["fuel_type"],
                mileage_kmpl=mileage_val,
                engine_cc=int(c.get("engine_cc", 1497)) if c.get("engine_cc") else None,
                seating_capacity=int(c.get("seating", 5)),
                transmission=c.get("transmission", ["Manual"])[0] if isinstance(c.get("transmission"), list) else "Manual",
                pros=c.get("best_for", ["High market popularity", "Vast Indian service network"]),
                cons=["Waiting period varies by variant"],
                match_score=scores[idx] if idx < len(scores) else 80.0,
                segment=c.get("segment", "Car")
            ))
        brands_list = sorted(list(set(c["brand"] for c in all_cars)))
        return CarRecommendationResponse(
            recommendations=recs[:3],
            summary=f"Automobile brands available in AutoBot database: {', '.join(brands_list)}.",
            top_pick=recs[0].car_name,
            buying_tips=[
                "Compare warranty & after-sales service across Maruti, Hyundai, Tata, Honda, Toyota, and Mahindra.",
                "Schedule test drives for short-listed models.",
            ]
        )

    # Extract max budget
    max_budget = 20.0
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l)', msg_lower)
    if match:
        max_budget = float(match.group(1))

    # Segment filter
    segment_filter = None
    for seg in ["suv", "sedan", "hatchback", "ev", "mpv", "muv"]:
        if seg in msg_lower:
            segment_filter = seg
            break

    matched_cars = [
        c for c in all_cars
        if c["price_lakh"]["min"] <= max_budget and (
            not segment_filter or
            segment_filter in c["segment"].lower() or
            segment_filter in c["name"].lower()
        )
    ]
    if not matched_cars:
        matched_cars = [c for c in all_cars if c["price_lakh"]["min"] <= max_budget]
    if not matched_cars:
        matched_cars = all_cars

    selected = matched_cars[:3]
    scores = [96.0, 91.0, 87.0]
    recs = []
    for idx, c in enumerate(selected):
        m = c.get("mileage_kmpl", 18.0)
        mileage_val = float(list(m.values())[0]) if isinstance(m, dict) and m else float(m) if m else 18.0
        recs.append(CarSpec(
            car_name=c["name"],
            brand=c["brand"],
            price_range=f"₹{c['price_lakh']['min']}L - ₹{c['price_lakh']['max']}L",
            fuel_type=c["fuel_type"][0] if isinstance(c["fuel_type"], list) else c["fuel_type"],
            mileage_kmpl=mileage_val,
            engine_cc=int(c.get("engine_cc", 1497)) if c.get("engine_cc") else None,
            seating_capacity=int(c.get("seating", 5)),
            transmission=c.get("transmission", ["Manual"])[0] if isinstance(c.get("transmission"), list) else "Manual",
            pros=c.get("best_for", ["Excellent road presence", "Spacious cabin", "High ground clearance"]),
            cons=["Slightly higher waiting period", "Base variant lacks touchscreen"],
            match_score=scores[idx],
            segment=c.get("segment", "SUV")
        ))

    return CarRecommendationResponse(
        recommendations=recs,
        summary=f"Recommended top vehicles for your search (budget up to ₹{max_budget} Lakhs).",
        top_pick=recs[0].car_name if recs else "Tata Nexon",
        buying_tips=[
            "Take a test drive during peak city traffic to check transmission response.",
            "Compare dealer quotes for optional accessories before finalizing.",
            "Inquire about festive and corporate discounts for lower overall price.",
        ]
    )
