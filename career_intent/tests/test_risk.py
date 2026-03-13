from career_intent.app.engines.risk import RiskInstabilityEngine


def test_detect_caution_window():
    engine = RiskInstabilityEngine(
        {
            "window": {"min_days": 3, "max_days": 4, "min_caution_score": 35},
            "normalization": {"risk": {"min": 0.0, "max": 10.0}},
        }
    )
    features = []
    for idx in range(10):
        features.append(
            {
                "date": f"2026-02-{idx+1:02d}",
                "opportunity_raw": 2.0,
                "risk_raw": 9.0 if idx >= 5 else 1.0,
                "drivers": ["Execution pressure"],
                "positive_drivers": ["Delivery support"] if idx < 3 else [],
                "negative_drivers": ["Execution pressure"],
                "evidence": {"Execution pressure": "High dependencies and compressed timelines"},
            }
        )
    series = engine.compute_time_series(features)
    ranked = engine.rank_candidates(series)
    window = engine.detect_caution_window(series)
    assert ranked
    assert window.score >= 70
    assert "Execution pressure" in window.top_drivers
    assert window.drivers_detail
