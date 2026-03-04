"""Unit tests for purchase_type functionality."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from spend_intel_engine.domain.enums import BASE_AMPLITUDE, RISK_MULTIPLIER, PurchaseType
from spend_intel_engine.domain.models import Driver, RuleMaps, ShoppingCfg, SpendProfile
from spend_intel_engine.scoring.daily_scorer import (
    _get_purchase_advice,
    _has_outer_planet_hard_aspect,
    score_daily_shopping,
)


def test_purchase_type_enum():
    """Test purchase type enum values."""
    assert PurchaseType.ESSENTIALS.value == "essentials"
    assert PurchaseType.BIG_TICKET.value == "big_ticket"
    assert PurchaseType.LUXURY.value == "luxury"


def test_base_amplitude_constants():
    """Test BASE_AMPLITUDE constants."""
    assert BASE_AMPLITUDE["essentials"] == 0.6
    assert BASE_AMPLITUDE["big_ticket"] == 1.0
    assert BASE_AMPLITUDE["luxury"] == 1.25


def test_risk_multiplier_constants():
    """Test RISK_MULTIPLIER constants."""
    assert RISK_MULTIPLIER["essentials"] == 0.7
    assert RISK_MULTIPLIER["big_ticket"] == 1.0
    assert RISK_MULTIPLIER["luxury"] == 1.4


def test_get_purchase_advice():
    """Test purchase-specific advice generation."""
    assert _get_purchase_advice("essentials") == "Safe for routine or necessary spending."
    assert _get_purchase_advice("big_ticket") == "Ensure planning and comparison before committing."
    assert _get_purchase_advice("luxury") == "Apply budget cap and cooling-off rule."
    assert _get_purchase_advice("unknown") == ""


def test_has_outer_planet_hard_aspect():
    """Test outer planet hard aspect detection."""
    assert _has_outer_planet_hard_aspect("VEN SQR NEP") is True
    assert _has_outer_planet_hard_aspect("MOO OPP PLU") is True
    assert _has_outer_planet_hard_aspect("SUN SQR URA") is True
    assert _has_outer_planet_hard_aspect("VEN TRI JUP") is False
    assert _has_outer_planet_hard_aspect("MOO CON SAT") is False


class MockLifeEvent:
    def __init__(self, aspect, start, end, exact, nature="Positive", event_type="MAJOR"):
        self.aspect = aspect
        self.startDate = start.isoformat()
        self.endDate = end.isoformat()
        self.exactDate = exact.isoformat()
        self.aspectNature = nature
        self.eventType = event_type
        self.description = "Test event"


def test_purchase_type_affects_scoring():
    """Test that purchase_type affects daily scores."""
    start = date(2026, 3, 1)
    n_days = 7
    
    profile = SpendProfile(
        score=50,
        category="Balanced",
        description="Test profile",
        top_drivers=[],
    )
    
    rule_maps = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={"VEN TRI JUP": "Good for purchases"},
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="test_v1",
    )
    
    events = [
        MockLifeEvent("VEN TRI JUP", start, start + timedelta(days=2), start + timedelta(days=1)),
    ]
    
    # Test essentials
    cfg_essentials = ShoppingCfg(purchase_type="essentials")
    scores_essentials = score_daily_shopping(events, start, n_days, profile, rule_maps, cfg_essentials)
    
    # Test luxury
    cfg_luxury = ShoppingCfg(purchase_type="luxury")
    scores_luxury = score_daily_shopping(events, start, n_days, profile, rule_maps, cfg_luxury)
    
    # Luxury should have higher scores than essentials for positive aspects
    # (due to higher BASE_AMPLITUDE)
    assert scores_luxury[1].score > scores_essentials[1].score


def test_impulsive_luxury_guardrail():
    """Test that Impulsive profile gets penalty for luxury purchases."""
    start = date(2026, 3, 1)
    n_days = 3
    
    profile = SpendProfile(
        score=85,
        category="Impulsive/High-Spend Risk",
        description="High risk profile",
        top_drivers=[],
    )
    
    rule_maps = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={},
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="test_v1",
    )
    
    # No events, so we can clearly see the guardrail effect
    events = []
    
    cfg_luxury = ShoppingCfg(purchase_type="luxury")
    scores_luxury = score_daily_shopping(events, start, n_days, profile, rule_maps, cfg_luxury)
    
    # Should have guardrail driver
    guardrail_drivers = [d for d in scores_luxury[0].top_drivers if d.code == "PROFILE_GUARDRAIL"]
    assert len(guardrail_drivers) > 0
    assert guardrail_drivers[0].weight < 0


def test_thrifty_essentials_boost():
    """Test that Ultra Thrifty profile gets boost for essentials."""
    start = date(2026, 3, 1)
    n_days = 3
    
    profile = SpendProfile(
        score=15,
        category="Ultra Thrifty",
        description="Very cautious",
        top_drivers=[],
    )
    
    rule_maps = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={},
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="test_v1",
    )
    
    events = []
    
    cfg_essentials = ShoppingCfg(purchase_type="essentials")
    scores_essentials = score_daily_shopping(events, start, n_days, profile, rule_maps, cfg_essentials)
    
    # Should have boost driver
    boost_drivers = [d for d in scores_essentials[0].top_drivers if d.code == "PROFILE_BOOST"]
    assert len(boost_drivers) > 0
    assert boost_drivers[0].weight > 0


def test_metrics_data_returned():
    """Test that metrics_data is returned from score_daily_shopping."""
    start = date(2026, 3, 1)
    n_days = 3
    
    profile = SpendProfile(score=50, category="Balanced", description="Test", top_drivers=[])
    rule_maps = RuleMaps(
        natal_spend_implications={},
        transit_daily_implications={},
        natal_structure_implications={},
        moon_spending_implications={},
        ruleset_version="test_v1",
    )
    
    events = []
    cfg = ShoppingCfg()
    
    scores, metrics_data = score_daily_shopping(
        events,
        start,
        n_days,
        profile,
        rule_maps,
        cfg,
        return_metrics=True,
    )
    
    assert "total_events" in metrics_data
    assert "mapped_events" in metrics_data
    assert "fallback_events" in metrics_data
    assert metrics_data["total_events"] == 0
