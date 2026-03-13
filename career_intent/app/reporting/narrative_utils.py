from __future__ import annotations

from html import escape
from typing import Dict, List


def dedupe_lines(items: List[str], fallback: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for raw in items:
        text = str(raw or "").strip()
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out if out else list(fallback)


def period_signal_label(opportunity_score: int, caution_score: int) -> str:
    if opportunity_score >= 70 and caution_score <= 45:
        return "high-opportunity"
    if caution_score >= 70 and opportunity_score <= 50:
        return "caution-led"
    if opportunity_score >= caution_score + 10:
        return "preparation"
    return "mixed"


def build_hero_narrative(
    *,
    user_name: str,
    primary_intent: str,
    timeframe_label: str,
    period_signal: str,
) -> str:
    if not user_name:
        user_name = "You"

    openers = [
        f"{user_name}, this {timeframe_label} is a meaningful career positioning phase.",
        f"{user_name}, your next {timeframe_label} can materially shift your trajectory if you act with focus.",
        f"{user_name}, your current {timeframe_label} is built for deliberate career moves, not scattered effort.",
    ]
    seed = sum(ord(char) for char in f"{user_name}|{primary_intent}|{timeframe_label}|{period_signal}")
    opener = openers[seed % len(openers)]

    period_clause = {
        "high-opportunity": "Signals are strongly supportive, so visible moves made in sequence can compound quickly.",
        "preparation": "Momentum is building, and disciplined preparation now can convert into stronger execution when the window opens.",
        "mixed": "Signals are mixed, which makes timing and sequencing more important than volume.",
        "caution-led": "Conditions are caution-led right now, so smart restraint and targeted preparation will protect your next major move.",
    }.get(period_signal, "Timing is meaningful, so sequence and clarity matter more than intensity.")

    goal_clause = (
        f"Your core priority is {primary_intent}, and this report translates that goal into date-bound decisions."
        if primary_intent
        else "This report turns your current career direction into date-bound decisions."
    )

    closing = "Use it to push where upside is real, prepare where leverage is building, and avoid commitments that dilute momentum."
    return " ".join([opener, goal_clause, period_clause, closing])


def build_kpi_explanation(
    *,
    label: str,
    score: int,
    positive_driver: str,
    negative_driver: str,
    direction_of_change: str,
) -> str:
    score_phrase = "strong" if score >= 70 else "developing" if score >= 50 else "fragile"
    parts = [f"{label} is {score_phrase} in this cycle."]
    if positive_driver:
        parts.append(f"The biggest support is {positive_driver.lower()}.")
    if negative_driver:
        parts.append(f"The main drag is {negative_driver.lower()}.")
    if direction_of_change:
        parts.append(direction_of_change)
    return " ".join(parts)


def build_driver_practical_meaning(driver: Dict, report_data: Dict) -> str:
    label = str(driver.get("label") or driver.get("driver_label") or "this factor").strip()
    category = str(driver.get("category") or "Execution").strip().lower()
    polarity = str(driver.get("polarity") or "").strip().lower()
    top_intent = ""
    intents = report_data.get("career_intent_scores") or []
    if intents:
        top_intent = str(intents[0].get("intent_name") or "").strip()

    if category == "opportunity" or polarity == "positive":
        tail = "use it to take visible, role-shaping actions while support is high"
    elif category in {"stability", "caution"} or polarity == "negative":
        tail = "tighten scope and reduce avoidable risk before making irreversible moves"
    else:
        tail = "treat it as an execution lever and align weekly choices around it"

    if top_intent:
        return f"{label} most directly affects your {top_intent} plan, so {tail}."
    return f"{label} influences near-term outcomes, so {tail}."


def build_closed_window_takeaway(
    *,
    window_label: str,
    next_window_label: str,
    primary_intent: str,
    strengths: List[str],
    gaps: List[str],
) -> str:
    strength_hint = strengths[0] if strengths else "execution discipline"
    gap_hint = gaps[0] if gaps else "decision clarity"
    intent_phrase = f"for {primary_intent}" if primary_intent else "for your core career move"
    return (
        f"The {window_label} window would have been ideal {intent_phrase} using your {strength_hint.lower()} as leverage. "
        f"The upcoming {next_window_label} window can still deliver strong outcomes if you reduce {gap_hint.lower()} before it opens."
    )


def html_list(items: List[str], *, prefix: str = "") -> str:
    return "".join(f"<li>{escape(prefix + item)}</li>" for item in items)
