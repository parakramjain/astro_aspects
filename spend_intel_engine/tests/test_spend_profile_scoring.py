from spend_intel_engine.domain.models import RuleMaps, ShoppingCfg
from spend_intel_engine.scoring.spend_profile_scorer import score_spend_profile
from spend_intel_engine.tests.test_fixtures import SampleAspect, sample_natal_chart


def test_score_clamping_and_category_mapping_high_risk():
    cfg = ShoppingCfg(
        natal_spend_aspects_csv="a.csv",
        transit_daily_shopping_aspects_csv="b.csv",
        natal_structure_signals_csv="c.csv",
        moon_spending_aspects_csv="d.csv",
        spend_scale=50,
    )
    rules = RuleMaps(
        natal_spend_implications={"VEN TRI JUP": "luxury and optimism"},
        transit_daily_implications={},
        natal_structure_implications={
            "VENUS_CONDITION": "pleasure orientation",
            "SATURN_PROMINENCE": "discipline",
            "JUPITER_PROMINENCE": "expansion",
            "SECOND_RULER_STABILITY": "resource planning",
            "EIGHTH_RULER_PRESSURE": "shared finance pressure",
        },
        moon_spending_implications={},
        ruleset_version="x",
    )

    natal_chart = sample_natal_chart()
    aspects = [SampleAspect(aspect="VEN TRI JUP", strength=1.0)]

    profile = score_spend_profile(natal_chart, aspects, rules, cfg)

    assert 0 <= profile.score <= 100
    assert profile.category in {
        "Ultra Thrifty",
        "Thrifty",
        "Balanced",
        "Spender",
        "Impulsive/High-Spend Risk",
    }
    assert profile.top_drivers


def test_score_clamping_low_end():
    cfg = ShoppingCfg(
        natal_spend_aspects_csv="a.csv",
        transit_daily_shopping_aspects_csv="b.csv",
        natal_structure_signals_csv="c.csv",
        moon_spending_aspects_csv="d.csv",
        spend_scale=60,
    )
    rules = RuleMaps(
        natal_spend_implications={"MER SQR SAT": "friction under constraints"},
        transit_daily_implications={},
        natal_structure_implications={
            "VENUS_CONDITION": "pleasure orientation",
            "SATURN_PROMINENCE": "discipline",
            "JUPITER_PROMINENCE": "expansion",
            "SECOND_RULER_STABILITY": "resource planning",
            "EIGHTH_RULER_PRESSURE": "shared finance pressure",
        },
        moon_spending_implications={},
        ruleset_version="x",
    )

    natal_chart = sample_natal_chart()
    aspects = [SampleAspect(aspect="MER SQR SAT", strength=1.0)]

    profile = score_spend_profile(natal_chart, aspects, rules, cfg)
    assert 0 <= profile.score <= 100
