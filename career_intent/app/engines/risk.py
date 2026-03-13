from __future__ import annotations

from collections import Counter
from typing import Dict, List

from career_intent.app.engines.types import DailyScore, WindowResult


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize(value: float, min_value: float, max_value: float) -> int:
    if max_value <= min_value:
        return 0
    clipped = _clip(value, min_value, max_value)
    return int(round(((clipped - min_value) / (max_value - min_value)) * 100.0))


class RiskInstabilityEngine:
    def __init__(self, config: Dict):
        self.config = config

    def compute_time_series(self, features_by_day: List[Dict]) -> List[DailyScore]:
        norm = self.config.get("normalization", {}).get("risk", {"min": 0.0, "max": 8.0})
        out: List[DailyScore] = []
        previous = 0.0
        for item in features_by_day:
            raw = float(item.get("risk_raw", 0.0))
            volatility = abs(raw - previous)
            combined = raw + 0.2 * volatility
            previous = raw
            out.append(
                DailyScore(
                    date=item["date"],
                    opportunity_raw=float(item.get("opportunity_raw", 0.0)),
                    risk_raw=combined,
                    opportunity_score=0,
                    risk_score=_normalize(combined, norm.get("min", 0.0), norm.get("max", 8.0)),
                    drivers=sorted(set(item.get("drivers", []))),
                    positive_drivers=sorted(set(item.get("positive_drivers", []))),
                    negative_drivers=sorted(set(item.get("negative_drivers", []))),
                    evidence=dict(item.get("evidence", {})),
                )
            )
        return out

    def rank_candidates(self, time_series_scores: List[DailyScore]) -> List[WindowResult]:
        if not time_series_scores:
            return []
        min_days = int(self.config.get("window", {}).get("min_days", 21))
        max_days = int(self.config.get("window", {}).get("max_days", 42))
        max_days = min(max_days, len(time_series_scores))
        min_days = min(min_days, max_days)

        ranked: List[WindowResult] = []
        for length in range(min_days, max_days + 1):
            for start_idx in range(0, len(time_series_scores) - length + 1):
                chunk = time_series_scores[start_idx : start_idx + length]
                avg = sum(item.risk_score for item in chunk) / float(length)
                negative_counter: Counter = Counter()
                evidence_map: Dict[str, str] = {}
                for item in chunk:
                    negative_counter.update(item.negative_drivers or item.drivers)
                    for label, snippet in item.evidence.items():
                        if label not in evidence_map and snippet:
                            evidence_map[label] = snippet

                top_drivers = [d for d, _ in sorted(negative_counter.items(), key=lambda x: (-x[1], x[0]))[:5]]
                details = []
                for label in top_drivers[:5]:
                    details.append(
                        {
                            "driver_label": label,
                            "category": "Stability",
                            "polarity": "negative",
                            "impact_score": int(round(avg)),
                            "evidence_snippet": str(evidence_map.get(label, ""))[:120],
                        }
                    )
                quality = int(round(min(100.0, avg * 0.7 + min(30.0, len(top_drivers) * 6.0))))
                ranked.append(
                    WindowResult(
                        start_date=chunk[0].date,
                        end_date=chunk[-1].date,
                        score=int(round(avg if avg >= 0 else 0)),
                        top_drivers=top_drivers[:5],
                        quality=quality,
                        drivers_detail=details,
                    )
                )

        ranked.sort(key=lambda row: (-row.score, -row.quality, row.start_date, row.end_date))
        return ranked

    def detect_caution_window(self, time_series_scores: List[DailyScore]) -> WindowResult:
        ranked = self.rank_candidates(time_series_scores)
        if not ranked:
            return WindowResult(start_date="", end_date="", score=0, top_drivers=[], quality=0, is_neutral=True)
        best = ranked[0]
        min_score = int(self.config.get("window", {}).get("min_caution_score", 35))
        if best.score < min_score:
            return WindowResult(
                start_date=best.start_date,
                end_date=best.end_date,
                score=best.score,
                top_drivers=best.top_drivers[:3],
                quality=best.quality,
                drivers_detail=best.drivers_detail,
                is_neutral=True,
            )
        return best
