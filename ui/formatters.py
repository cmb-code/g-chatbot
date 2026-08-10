"""
ui/formatters.py — GFM Markdown Response Formatters

Converts structured Pydantic response objects into rich
GitHub-Flavored Markdown strings for display in Gradio.
"""


def format_car_recommendation(data) -> str:
    lines = [
        f"### 🏆 Top Pick: **{data.top_pick}**\n{data.summary}\n"
    ]
    scores_emoji = ["🥇", "🥈", "🥉"]
    for i, car in enumerate(data.recommendations):
        medal = scores_emoji[i] if i < 3 else "🚗"
        score_pct = int(car.match_score)

        pros_str = " · ".join(f"`✓ {p}`" for p in car.pros)
        cons_str = " · ".join(f"`✗ {c}`" for c in car.cons)

        lines.append(f"""
---
#### {medal} {car.car_name} &nbsp;·&nbsp; *{car.segment}*

| Key Specification | Details |
|:---|:---|
| 💰 **Price Range** | **{car.price_range}** |
| ⛽ **Fuel & Transmission** | {car.fuel_type} • {car.transmission} |
| 📊 **Mileage & Engine** | {car.mileage_kmpl} km/l {f"({car.engine_cc}cc)" if car.engine_cc else ""} |
| 💺 **Seating Capacity** | {car.seating_capacity} Seats |
| 🎯 **Match Score** | **{score_pct}/100** &nbsp; `{"▓" * (score_pct // 10)}{"░" * (10 - score_pct // 10)}` |

**Key Pros:** {pros_str}

**Considerations:** {cons_str}
""")

    tips_str = "\n".join(f"- {t}" for t in data.buying_tips)
    lines.append(f"\n---\n> 💡 **Buyer's Expert Tips**\n{tips_str}")
    return "\n".join(lines)


def format_diagnostic(data) -> str:
    sev_badge = {"Low": "🟢 Low", "Medium": "🟡 Medium", "High": "🔴 High", "Critical": "⛔ CRITICAL"}.get(data.severity, data.severity)
    drive_badge = "🟢 Safe to Drive (Get Checked)" if data.can_drive else "🔴 **DO NOT DRIVE — Arrange Towing**"

    causes_str = "\n".join(f"- {c}" for c in data.possible_causes)
    parts_str = ", ".join(f"`🔩 {p}`" for p in data.parts_that_may_need_replacement) if data.parts_that_may_need_replacement else "None"

    return f"""
### 🔧 Diagnostic Report — `{data.symptom_described}`

| Diagnostic Parameter | Assessment |
|:---|:---|
| ⚠️ **Severity** | **{sev_badge}** |
| 🎯 **Most Likely Cause** | **{data.most_likely_cause}** |
| 💸 **Est. Repair Cost** | **{data.estimated_repair_cost}** |
| ⏱️ **Urgency** | {data.urgency} |
| 🚗 **Driving Safety** | {drive_badge} |

#### 🔍 All Possible Causes
{causes_str}

#### 🔩 Replacement Parts Needed
{parts_str}

> 🗣️ **What to Tell Your Mechanic:**
> "{data.workshop_recommendation}"
"""


def format_service_schedule(data) -> str:
    status_icon = {"OK": "✅ OK", "Due Soon": "🟡 Due Soon", "Overdue": "🔴 Overdue"}
    table_rows = []
    for item in data.service_items:
        st = status_icon.get(item.status, item.status)
        table_rows.append(f"| {item.item_name} | {item.interval_km:,} km | `{st}` | **{item.estimated_cost}** |")

    table_str = "\n".join(table_rows)
    notes_str = "\n".join(f"- {n}" for n in data.important_notes)

    return f"""
### 📅 Service Schedule — **{data.car_name}**
**Current Odometer:** `{data.current_mileage:,} km`

| Service Item | Interval | Status | Est. Cost |
|:---|:---|:---|:---|
{table_str}

| Summary | Details |
|:---|:---|
| ⏳ **Next Major Service** | **{data.next_service_due}** |
| 💰 **Total Est. Cost** | **{data.total_estimated_cost}** |

> 📝 **Service Advisor Notes:**
{notes_str}
"""


def format_emi(data) -> str:
    tips_str = "\n".join(f"- {t}" for t in data.tips)

    return f"""
### 💰 Car Loan & EMI Estimate — **{data.car_name}**

## 💳 Monthly EMI: **{data.monthly_emi}**
*Tenure: {data.tenure_months} Months @ {data.interest_rate}% Interest p.a.*

| Financial Parameter | Amount |
|:---|:---|
| 🏷️ **On-Road Price** | {data.on_road_price} |
| 💵 **Down Payment** | **{data.down_payment}** |
| 🏦 **Loan Amount** | {data.loan_amount} |
| 📈 **Total Interest Outgo** | {data.total_interest} |
| 💳 **Total Amount Paid** | {data.total_amount_paid} |

#### 📊 Affordability Assessment
{data.affordability_check}

> 💡 **Finance Pro Tips:**
{tips_str}
"""


def format_general(data) -> str:
    questions_str = "\n".join(f"- {q}" for q in data.follow_up_questions)

    return f"""
### 💬 {data.category} &nbsp;·&nbsp; *Confidence: {data.confidence}*

{data.answer}

---
#### ❓ You might also want to ask:
{questions_str}
"""


def format_multi_intent(data) -> str:
    """Formats aggregated multi-intent results from parallel sub-agents into a combined document."""
    blocks = []
    for intent, result_obj in data.results.items():
        formatter = FORMATTERS.get(intent, format_general)
        formatted_block = formatter(result_obj)
        blocks.append(formatted_block)
    return "\n\n" + "\n\n---\n\n".join(blocks)


# Intent → formatter mapping
FORMATTERS = {
    "recommend": format_car_recommendation,
    "diagnostic": format_diagnostic,
    "service": format_service_schedule,
    "emi": format_emi,
    "general": format_general,
    "multi_intent": format_multi_intent,
}
