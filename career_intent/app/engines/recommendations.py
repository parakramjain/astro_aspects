from __future__ import annotations

from typing import Dict, List

from career_intent.app.engines.types import WindowResult


class ActionRecommendationGenerator:
    def __init__(self, config: Dict):
        self.config = config

    def generate(
        self,
        *,
        score_breakdown: Dict[str, int],
        top_intents: List[Dict],
        opportunity_window: WindowResult,
        caution_window: WindowResult,
    ) -> Dict[str, List[str]]:
        cfg = self.config.get("recommendations", {})
        min_bullets = int(cfg.get("min_bullets", 4))
        max_bullets = int(cfg.get("max_bullets", 7))
        verbs = [str(v) for v in cfg.get("verbs", ["Apply", "Prepare", "Review", "Track"])]
        intent_actions = cfg.get("intent_actions", {})

        top_two = top_intents[:2]
        top_names = [row.get("intent_name", "") for row in top_two]

        def _prefixed(verb: str, text: str) -> str:
            return f"{verb} {text}".strip()

        bullets: List[str] = []
        if top_two:
            bullets.append(
                _prefixed(
                    verbs[0],
                    f"during {opportunity_window.start_date} to {opportunity_window.end_date}: {intent_actions.get(top_names[0], 'execute the highest-priority career move')}",
                )
            )
        if len(top_two) > 1:
            bullets.append(
                _prefixed(
                    verbs[1],
                    f"before {opportunity_window.start_date}: {intent_actions.get(top_names[1], 'prepare supporting evidence and stakeholder context')}",
                )
            )

        for driver in opportunity_window.top_drivers[:2]:
            bullets.append(_prefixed(verbs[2], f"during {opportunity_window.start_date} to {opportunity_window.end_date}, actions that increase {driver.lower()}.") )

        for driver in caution_window.top_drivers[:2]:
            bullets.append(_prefixed(verbs[6] if len(verbs) > 6 else "Pause", f"during {caution_window.start_date} to {caution_window.end_date}, non-essential moves affected by {driver.lower()}.") )

        bullets.append(
            _prefixed(
                verbs[-1],
                f"weekly metrics from now until {opportunity_window.end_date} to keep timing strength and stability aligned.",
            )
        )

        deduped: List[str] = []
        for bullet in bullets:
            text = bullet.strip()
            if text and text not in deduped:
                deduped.append(text)

        bounded = deduped[:max_bullets]
        while len(bounded) < min_bullets:
            bounded.append("Review weekly progress against specific outcomes and adjust execution scope.")

        action_plan = {
            "now_to_opportunity_start": [
                f"Prepare a decision brief before {opportunity_window.start_date} with target roles, scope, and constraints.",
                "Build measurable proof of impact for your top-two priorities.",
                "Validate execution risks with one stakeholder check-in each week.",
            ],
            "during_opportunity": [
                f"Apply focused effort during {opportunity_window.start_date} to {opportunity_window.end_date} on high-leverage outcomes.",
                "Negotiate commitments with clear success criteria and timelines.",
                "Track weekly response signals and prioritize the strongest channel.",
            ],
            "during_caution": [
                f"Pause irreversible decisions during {caution_window.start_date} to {caution_window.end_date} unless critical.",
                "Review assumptions using small validation steps before expanding scope.",
                "Track workload pressure and remove low-impact commitments.",
            ],
        }
        return {"summary": bounded, "action_plan": action_plan}
