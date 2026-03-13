from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from career_intent.app.engines.types import FeatureSummary
from career_intent.app.features.report_parser import DeterministicReportParser
from career_intent.app.utils.dates import iter_days


@dataclass
class FeatureBuildResult:
    features_by_day: List[Dict]
    summary: FeatureSummary


class FeatureBuilder:
    def __init__(self, parser: DeterministicReportParser):
        self.parser = parser

    def _to_date(self, value) -> dt.date | None:
        if value is None:
            return None
        text = str(value)[:10]
        try:
            return dt.date.fromisoformat(text)
        except ValueError:
            return None

    def build(
        self,
        *,
        items: List[Dict],
        start_date: dt.date,
        end_date: dt.date,
    ) -> FeatureBuildResult:
        days: Dict[str, Dict] = {}
        for day in iter_days(start_date, end_date):
            iso = day.isoformat()
            days[iso] = {
                "date": iso,
                "opportunity_raw": 0.0,
                "risk_raw": 0.0,
                "drivers": [],
                "positive_drivers": [],
                "negative_drivers": [],
                "evidence": {},
                "positive_count": 0,
                "negative_count": 0,
            }

        positive_count = 0
        negative_count = 0
        neutral_count = 0
        driver_counter: Counter = Counter()
        matched_driver_count = 0
        data_quality_flags: List[str] = []

        if not items:
            data_quality_flags.append("report_text_only")

        for item in items:
            start = self._to_date(item.get("startDate"))
            end = self._to_date(item.get("endDate"))
            if not start or not end:
                continue
            nature = str(item.get("aspectNature", "")).strip().lower()
            description = str(item.get("description", ""))
            drivers_meta = self.parser.extract_drivers(description)
            if not drivers_meta:
                data_quality_flags.append("parser_fallback")
                if nature == "positive":
                    drivers_meta = [self.parser.fallback_driver_meta("positive")]
                elif nature == "negative":
                    drivers_meta = [self.parser.fallback_driver_meta("negative")]
                else:
                    drivers_meta = [
                        {
                            "driver_label": "Operational focus",
                            "driver_category": "Execution",
                            "polarity": "positive",
                            "matched_pattern": "fallback",
                        }
                    ]

            score_opp = 1.0 if nature == "positive" else 0.25 if nature == "neutral" else 0.0
            score_risk = 1.0 if nature == "negative" else 0.15
            if nature == "positive":
                positive_count += 1
            elif nature == "negative":
                negative_count += 1
            else:
                neutral_count += 1

            clip_start = max(start, start_date)
            clip_end = min(end, end_date)
            cur = clip_start
            while cur <= clip_end:
                day = days[cur.isoformat()]
                day["opportunity_raw"] += score_opp
                day["risk_raw"] += score_risk
                for meta in drivers_meta:
                    label = meta["driver_label"]
                    polarity = str(meta.get("polarity", "positive")).lower()
                    pattern = str(meta.get("matched_pattern", ""))
                    day["drivers"].append(label)
                    if polarity == "negative":
                        day["negative_drivers"].append(label)
                    else:
                        day["positive_drivers"].append(label)
                    if label not in day["evidence"]:
                        day["evidence"][label] = self.parser.evidence_snippet(description, pattern)
                if nature == "positive":
                    day["positive_count"] += 1
                if nature == "negative":
                    day["negative_count"] += 1
                cur += dt.timedelta(days=1)
            driver_labels = [meta["driver_label"] for meta in drivers_meta]
            driver_counter.update(driver_labels)
            matched_driver_count += len(driver_labels)

        ordered_days = [days[key] for key in sorted(days.keys())]
        total = positive_count + negative_count + neutral_count
        confidence = 0.0 if total == 0 else min(1.0, total / 20.0)
        drivers_expected = max(1, total * 2)
        drivers_coverage = min(1.0, matched_driver_count / float(drivers_expected))

        timing_strength = 0.0
        execution_stability = 0.0
        risk_pressure = 0.0
        growth_leverage = 0.0
        if ordered_days:
            opp_avg = sum(float(day["opportunity_raw"]) for day in ordered_days) / len(ordered_days)
            risk_avg = sum(float(day["risk_raw"]) for day in ordered_days) / len(ordered_days)
            deltas = []
            prev = None
            for day in ordered_days:
                if prev is not None:
                    deltas.append(abs(float(day["opportunity_raw"]) - prev))
                prev = float(day["opportunity_raw"])
            volatility = (sum(deltas) / len(deltas)) if deltas else 0.0

            timing_strength = max(0.0, min(100.0, 30.0 + opp_avg * 12.0))
            execution_stability = max(0.0, min(100.0, 80.0 - volatility * 12.0))
            risk_pressure = max(0.0, min(100.0, 20.0 + risk_avg * 14.0))
            growth_leverage = max(0.0, min(100.0, 20.0 + (positive_count - negative_count) * 4.0 + opp_avg * 8.0))

        summary = FeatureSummary(
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            confidence=confidence,
            driver_counts={k: driver_counter[k] for k in sorted(driver_counter.keys())},
            drivers_coverage=drivers_coverage,
            data_quality_flags=sorted(set(data_quality_flags)),
            dimension_signals={
                "timing_strength": timing_strength,
                "execution_stability": execution_stability,
                "risk_pressure": risk_pressure,
                "growth_leverage": growth_leverage,
            },
        )
        return FeatureBuildResult(features_by_day=ordered_days, summary=summary)
