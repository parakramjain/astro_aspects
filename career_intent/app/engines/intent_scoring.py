from __future__ import annotations

from typing import Dict, List

from career_intent.app.engines.types import WindowResult


def _clip_0_100(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


class CareerIntentScoringEngine:
    def __init__(self, config: Dict):
        self.config = config

    def compute(
        self,
        *,
        score_breakdown: Dict[str, int],
        opportunity_window: WindowResult,
        risk_window: WindowResult,
    ) -> List[Dict]:
        weights = self.config.get("weights", {})
        defaults = weights.get("intent_defaults", {})
        intents = weights.get("intents", {})

        timing_strength = float(score_breakdown.get("timing_strength", 0))
        execution_stability = float(score_breakdown.get("execution_stability", 0))
        risk_pressure = float(score_breakdown.get("risk_pressure", 0))
        growth_leverage = float(score_breakdown.get("growth_leverage", 0))
        risk_inverse = 100.0 - risk_pressure

        reason_templates = {
            "Job Change": "Role-shift readiness is driven by timing strength and growth leverage with controlled risk pressure.",
            "Promotion": "Advancement potential improves when execution stability and timing strength are both elevated.",
            "Entrepreneurship": "Independent-path potential depends on growth leverage and willingness to operate under pressure.",
            "Skill Building": "Capability compounding is strongest when growth leverage is high and caution is used productively.",
            "Exploration / Discovery": "Exploration quality improves when timing is moderate and decisions are validated before commitment.",
            "Networking / Positioning": "Positioning outcomes improve when timing supports outreach and communication discipline remains high.",
            "Side Project / Testing the Waters": "Pilot initiatives perform best when growth potential is present but risk is staged carefully.",
            "Transition / In Between": "Transition readiness improves when stability planning offsets elevated uncertainty.",
        }

        next_steps = {
            "Job Change": "Apply to three high-fit roles during the opportunity window and track response quality weekly.",
            "Promotion": "Negotiate measurable impact targets with leadership before the opportunity window midpoint.",
            "Entrepreneurship": "Validate your offer with five target users before committing additional capital or time.",
            "Skill Building": "Build one portfolio-grade deliverable tied to your target role before the window starts.",
            "Exploration / Discovery": "Review two career tracks and validate each with one real-world experiment.",
            "Networking / Positioning": "Network with five relevant decision-makers and follow up within 72 hours.",
            "Side Project / Testing the Waters": "Build a low-risk pilot and track two traction indicators each week.",
            "Transition / In Between": "Prepare a transition plan covering timeline, runway, and fallback options.",
        }

        rows: List[Dict] = []
        for intent_name in sorted(intents.keys()):
            w = {**defaults, **intents.get(intent_name, {})}
            score = (
                float(w.get("timing_strength", 0.30)) * timing_strength
                + float(w.get("execution_stability", 0.25)) * execution_stability
                + float(w.get("risk_inverse", 0.20)) * risk_inverse
                + float(w.get("growth_leverage", 0.25)) * growth_leverage
            )
            final = _clip_0_100(score)
            recommended_window = "neutral"
            if opportunity_window.score >= max(50, risk_window.score + 5):
                recommended_window = "opportunity"
            elif risk_window.score >= max(50, opportunity_window.score + 5):
                recommended_window = "caution"

            reason_prefix = reason_templates.get(intent_name, "Intent fit is based on timing, stability, risk, and growth signals.")
            reason = (
                f"{reason_prefix} "
                f"Current profile: timing {int(timing_strength)}, stability {int(execution_stability)}, "
                f"risk pressure {int(risk_pressure)}, growth leverage {int(growth_leverage)}."
            )
            rows.append(
                {
                    "intent_name": intent_name,
                    "score": final,
                    "short_reason": reason,
                    "recommended_window": recommended_window,
                    "next_step": next_steps.get(intent_name, "Track weekly outcomes and adapt execution plan."),
                }
            )

        rows.sort(key=lambda item: (-item["score"], item["intent_name"]))
        return rows
