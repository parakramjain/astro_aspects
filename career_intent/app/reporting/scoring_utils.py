from __future__ import annotations

import datetime as dt
from typing import Dict, List, Tuple

from .date_utils import overlap_days, to_date


def _bounded_int(value: float, *, lower: int = 0, upper: int = 100) -> int:
    return max(lower, min(upper, int(round(value))))


def rank_and_spread_driver_scores(drivers: List[Dict]) -> List[Dict]:
    if not drivers:
        return []

    scored: List[Dict] = []
    for row in drivers:
        raw_score = float(row.get("impact_score", 0) or 0)
        label = str(row.get("label") or row.get("driver_label") or "").strip()
        category = str(row.get("category") or "General").strip()
        if not label:
            continue
        key_bias = (sum(ord(ch) for ch in (label + category)) % 7) / 10.0
        scored.append({
            **row,
            "label": label,
            "category": category,
            "raw_score": raw_score,
            "sort_score": raw_score + key_bias,
        })

    if not scored:
        return []

    ranked = sorted(scored, key=lambda item: (-item["sort_score"], item["label"].lower(), item["category"].lower()))

    n = len(ranked)
    min_band = 46
    max_band = 94
    step = (max_band - min_band) / max(n - 1, 1)

    raw_values = [float(item["raw_score"]) for item in ranked]
    raw_min = min(raw_values)
    raw_max = max(raw_values)

    previous_value = 101
    for idx, item in enumerate(ranked):
        base = max_band - (idx * step)
        if raw_max > raw_min:
            norm = (item["raw_score"] - raw_min) / (raw_max - raw_min)
            raw_adjust = (norm - 0.5) * 2.4
        else:
            raw_adjust = 0.0

        spread = _bounded_int(base + raw_adjust)
        if spread >= previous_value:
            spread = max(min_band, previous_value - 1)
        item["impact_score"] = spread
        previous_value = spread

    return ranked


def _intent_window_range(intent: Dict, opportunity_window: Dict, caution_window: Dict) -> Tuple[dt.date | None, dt.date | None]:
    start = to_date(str(intent.get("window_start") or intent.get("start_date") or ""))
    end = to_date(str(intent.get("window_end") or intent.get("end_date") or ""))
    if start and end:
        return start, end

    recommended = str(intent.get("recommended_window") or "").strip().lower()
    if recommended == "opportunity":
        return to_date(str(opportunity_window.get("start_date") or "")), to_date(str(opportunity_window.get("end_date") or ""))
    if recommended == "caution":
        return to_date(str(caution_window.get("start_date") or "")), to_date(str(caution_window.get("end_date") or ""))
    return None, None


def pick_top_priority_intent(
    intents: List[Dict],
    *,
    opportunity_window: Dict,
    caution_window: Dict,
    report_date: dt.date,
) -> Dict | None:
    if not intents:
        return None

    caution_start = to_date(str(caution_window.get("start_date") or ""))
    caution_end = to_date(str(caution_window.get("end_date") or ""))
    caution_range = (caution_start, caution_end) if caution_start and caution_end else None

    candidates: List[Tuple] = []
    for row in intents:
        score = int(row.get("score", 0) or 0)
        start, end = _intent_window_range(row, opportunity_window, caution_window)
        feasibility = float(row.get("feasibility") or row.get("feasibility_score") or 50)
        overlap = overlap_days((start, end) if start and end else None, caution_range)
        if start:
            days_until = (start - report_date).days
            earliest_bias = days_until if days_until >= 0 else 9999
        else:
            earliest_bias = 9999
        candidates.append((
            -score,
            earliest_bias,
            -feasibility,
            overlap,
            str(row.get("intent_name") or "").lower(),
            row,
        ))

    candidates.sort(key=lambda item: item[:-1])
    return candidates[0][-1] if candidates else None


def direction_of_change(*, report_date: dt.date, opportunity_start: dt.date | None, caution_start: dt.date | None) -> str:
    if opportunity_start and report_date < opportunity_start:
        return f"Timing support improves after {opportunity_start.strftime('%b %d, %Y')}."
    if caution_start and report_date < caution_start:
        return f"Conditions tighten after {caution_start.strftime('%b %d, %Y')}."
    if caution_start and report_date >= caution_start:
        return "This signal may weaken during the current caution span."
    return "Momentum is steady across this report window."
