from career_intent.app.engines.momentum import CareerMomentumEngine


def test_momentum_in_range():
    engine = CareerMomentumEngine(
        {
            "weights": {
                "momentum": {
                    "timing_strength": 0.35,
                    "execution_stability": 0.30,
                    "inverse_risk_pressure": 0.20,
                    "growth_leverage": 0.15,
                }
            }
        }
    )
    score = engine.compute(
        timing_strength=74,
        execution_stability=68,
        risk_pressure=35,
        growth_leverage=72,
    )
    assert 0 <= score <= 100
    assert score > 50
