from career_intent.app.engines.intent_scoring import CareerIntentScoringEngine
from career_intent.app.engines.types import WindowResult


def test_intent_scoring_sorted_desc():
    engine = CareerIntentScoringEngine(
        {
            "weights": {
                "intent_defaults": {
                    "positive_count": 0.35,
                    "risk_inverse": 0.20,
                    "opportunity_window": 0.25,
                    "stability": 0.20,
                },
                "intents": {
                    "Skill Building": {"positive_count": 0.30},
                    "Promotion": {"positive_count": 0.40},
                },
            }
        }
    )
    rows = engine.compute(
        score_breakdown={
            "timing_strength": 78,
            "execution_stability": 71,
            "risk_pressure": 34,
            "growth_leverage": 75,
        },
        opportunity_window=WindowResult("2026-01-01", "2026-01-30", 80, []),
        risk_window=WindowResult("2026-02-01", "2026-02-20", 40, []),
    )
    assert len(rows) == 2
    assert rows[0]["score"] >= rows[1]["score"]
    assert rows[0]["short_reason"] != rows[1]["short_reason"]
    assert rows[0]["recommended_window"] in {"opportunity", "caution", "neutral"}
