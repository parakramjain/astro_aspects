from career_intent.app.engines.recommendations import ActionRecommendationGenerator
from career_intent.app.engines.types import WindowResult


def test_recommendations_constraints():
    engine = ActionRecommendationGenerator(
        {
            "recommendations": {
                "min_bullets": 4,
                "max_bullets": 6,
                "verbs": ["Apply", "Prepare", "Review", "Track", "Validate", "Pause"],
                "intent_actions": {
                    "Networking / Positioning": "Network with relevant stakeholders and keep outreach disciplined."
                },
            }
        }
    )
    recs_payload = engine.generate(
        score_breakdown={"timing_strength": 75, "execution_stability": 70, "risk_pressure": 35, "growth_leverage": 72},
        top_intents=[{"intent_name": "Networking / Positioning", "score": 80}],
        opportunity_window=WindowResult("2026-01-01", "2026-01-20", 78, ["Growth and expansion"]),
        caution_window=WindowResult("2026-02-01", "2026-02-20", 65, ["Execution pressure"]),
    )
    recs = recs_payload["summary"]
    assert 4 <= len(recs) <= 6
    assert all(isinstance(item, str) for item in recs)
    assert len(recs) == len(set(recs))
    assert "action_plan" in recs_payload
