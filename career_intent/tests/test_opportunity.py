from career_intent.app.engines.opportunity import OpportunityWindowEngine


def test_detect_best_opportunity_window():
    engine = OpportunityWindowEngine(
        {
            "window": {"min_days": 3, "max_days": 5, "smoothing_days": 1, "min_opportunity_score": 45},
            "normalization": {"opportunity": {"min": 0.0, "max": 10.0}},
        }
    )
    features = []
    for idx in range(10):
        features.append(
            {
                "date": f"2026-01-{idx+1:02d}",
                "opportunity_raw": 8.0 if 3 <= idx <= 6 else 2.0,
                "risk_raw": 1.0,
                "drivers": ["Growth and expansion"],
                "positive_drivers": ["Growth and expansion"],
                "negative_drivers": ["Execution pressure"] if idx < 2 else [],
                "evidence": {"Growth and expansion": "Strong demand and visibility"},
            }
        )

    series = engine.compute_time_series(features)
    ranked = engine.rank_candidates(series)
    window = engine.detect(series)
    assert ranked
    assert window.score >= 70
    assert window.start_date <= window.end_date
    assert 0 <= window.quality <= 100
    assert window.drivers_detail
