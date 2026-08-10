"""
agents/emi_agent.py — EMI / Finance Handler

Handles the "emi" intent using pure arithmetic — no LLM needed.
Extracts loan parameters from the user message and computes EMI directly.

Why no Pydantic AI Agent?
  EMI is 100% deterministic math: P * r * (1+r)^n / ((1+r)^n - 1).
  Spinning up an agent wastes 1-2 seconds and tokens just to call
  a math function we can call directly. This is instant (<1ms) and
  costs zero API quota.
"""

import re

from models.schemas import EMICalculationResponse
from tools.car_tools import calculate_emi


# ─────────────────────────────────────────────
# Direct Math Handler
# ─────────────────────────────────────────────

def handle_emi(user_message: str) -> EMICalculationResponse:
    """
    Compute EMI from user message. Extracts numbers via regex heuristics
    and calls calculate_emi() for the actual math.
    """
    msg_lower = user_message.lower()

    # Try to find a named car first
    car_name = "Vehicle"
    known_cars = [
        "creta", "nexon", "swift", "city", "scorpio", "xuv700", "seltos",
        "brezza", "punch", "tiago", "altroz", "venue", "i20", "baleno",
    ]
    for car in known_cars:
        if car in msg_lower:
            car_name = car.title()
            break

    # Extract numbers from the message
    numbers = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', user_message)]

    # Defaults
    price_lakh = 12.0
    annual_rate = 8.75
    tenure_months = 60

    # Find price (near "lakh" keyword or first large-ish number)
    lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs?|l)\b', msg_lower)
    if lakh_match:
        price_lakh = float(lakh_match.group(1))
    elif numbers:
        for n in numbers:
            if 3 <= n <= 200:
                price_lakh = n if n <= 200 else n / 100000
                break

    # Find interest rate (e.g. 8.5%)
    rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', user_message)
    if rate_match:
        annual_rate = float(rate_match.group(1))

    # Find tenure in years or months
    tenure_yr_match = re.search(r'(\d+)\s*(?:year|yr|years)', msg_lower)
    tenure_mo_match = re.search(r'(\d+)\s*(?:month|months|mo)', msg_lower)
    if tenure_yr_match:
        tenure_months = int(tenure_yr_match.group(1)) * 12
    elif tenure_mo_match:
        tenure_months = int(tenure_mo_match.group(1))

    # Standard Indian car loan: 20% down, 80% financed, ~8% on-road markup
    on_road_lakh = price_lakh * 1.08
    down_pct = 0.20
    down_lakh = on_road_lakh * down_pct
    principal = (on_road_lakh - down_lakh) * 100_000  # in INR

    result = calculate_emi(principal, annual_rate, tenure_months)

    # Affordability rule: EMI ≤ 20% of take-home salary
    monthly_emi_raw = result["monthly_emi_raw"]
    min_income = monthly_emi_raw / 0.20
    affordability = (
        f"At ₹{monthly_emi_raw:,.0f}/month EMI, you need a minimum take-home salary of "
        f"₹{min_income:,.0f}/month (EMI ≤ 20% of income rule). "
        f"Comfortable salary: ₹{min_income * 1.3:,.0f}+/month."
    )

    return EMICalculationResponse(
        car_name=car_name,
        on_road_price=f"₹{on_road_lakh:.2f} Lakhs (approx. with taxes & insurance)",
        down_payment=f"₹{down_lakh:.2f} Lakhs (20%)",
        loan_amount=f"₹{(on_road_lakh - down_lakh):.2f} Lakhs (80%)",
        interest_rate=annual_rate,
        tenure_months=tenure_months,
        monthly_emi=result["monthly_emi"],
        total_interest=result["total_interest"],
        total_amount_paid=result["total_payment"],
        affordability_check=affordability,
        tips=[
            "Increase down payment to 25-30% to significantly cut total interest outgo.",
            "Compare interest rates: PSU banks (SBI, BOB) often offer 0.25-0.5% lower than private banks.",
            "Opt for shorter tenure if EMI is affordable — saves lakhs in interest.",
            "Pre-pay lump sums (bonus, incentives) to reduce principal early.",
            f"For ₹{price_lakh:.0f}L car: compare on-road quotes from at least 2 dealers before financing.",
        ]
    )
