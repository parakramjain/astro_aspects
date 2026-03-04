from datetime import date

from spend_intel_engine.domain.models import RuleMaps, ShoppingCfg, SpendProfile
from spend_intel_engine.scoring.daily_scorer import score_daily_shopping
from spend_intel_engine.tests.test_fixtures import SampleLifeEvent


def test_date_range_scoring_peaks_at_exact_date():
    cfg = ShoppingCfg(
        natal_spend_aspects_csv="a.csv",
        transit_daily_shopping_aspects_csv="b.csv",
        natal_structure_signals_csv="c.csv",
        moon_spending_aspects_csv="d.csv",
    )
    profile = SpendProfile(score=50, category="Balanced", description="", top_drivers=[])
    rules = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={"JUP SEX MAR": "supports planned buying"},
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="x",
    )

    events = [
        SampleLifeEvent(
            aspect="Jup Sxt Mar",
            aspectNature="Positive",
            startDate="2026-02-20",
            endDate="2026-02-24",
            exactDate="2026-02-22",
            eventType="MAJOR",
            description="good",
        )
    ]

    daily = score_daily_shopping(events, start_date=date(2026, 2, 20), n_days=5, profile=profile, rule_maps=rules, cfg=cfg)
    by_date = {item.date.isoformat(): item.score for item in daily}

    assert by_date["2026-02-22"] >= by_date["2026-02-21"]
    assert by_date["2026-02-22"] >= by_date["2026-02-23"]


def test_symmetric_mapping_applies_for_transit_implication():
    cfg = ShoppingCfg(
        natal_spend_aspects_csv="a.csv",
        transit_daily_shopping_aspects_csv="b.csv",
        natal_structure_signals_csv="c.csv",
        moon_spending_aspects_csv="d.csv",
    )
    profile = SpendProfile(score=50, category="Balanced", description="", top_drivers=[])
    rules = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={"VEN TRI JUP": "favorable discretionary spending"},
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="x",
    )

    events = [
        SampleLifeEvent(
            aspect="Jup Tri Ven",
            aspectNature="Positive",
            startDate="2026-02-20",
            endDate="2026-02-20",
            exactDate="2026-02-20",
            eventType="MAJOR",
            description="nice",
        )
    ]

    daily = score_daily_shopping(events, start_date=date(2026, 2, 20), n_days=1, profile=profile, rule_maps=rules, cfg=cfg)
    assert daily[0].top_drivers
    assert "favorable discretionary spending" in daily[0].top_drivers[0].implication
