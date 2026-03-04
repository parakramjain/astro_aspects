"""Unit tests for ops module - drift detection and metrics."""
from __future__ import annotations

from datetime import date

import pytest

from spend_intel_engine.domain.models import DailyScore, Driver, InsightsMetrics
from spend_intel_engine.ops.drift import detect_ruleset_shift
from spend_intel_engine.ops.metrics import compute_metrics


class MockLifeEvent:
    def __init__(self, nature="Positive"):
        self.aspectNature = nature


def test_detect_ruleset_shift_mean():
    """Test drift detection based on mean shift."""
    prev = {"mean": 50.0, "std": 10.0}
    
    # No shift
    current_no_shift = {"mean": 52.0, "std": 10.0}
    assert detect_ruleset_shift(prev, current_no_shift) is False
    
    # Significant shift (>8 points)
    current_shift = {"mean": 60.0, "std": 10.0}
    assert detect_ruleset_shift(prev, current_shift) is True


def test_detect_ruleset_shift_std():
    """Test drift detection based on std dev change."""
    prev = {"mean": 50.0, "std": 10.0}
    
    # No significant std change
    current_small = {"mean": 50.0, "std": 11.0}
    assert detect_ruleset_shift(prev, current_small) is False
    
    # Significant std change (>20%)
    current_large = {"mean": 50.0, "std": 13.0}
    assert detect_ruleset_shift(prev, current_large) is True


def test_detect_ruleset_shift_both():
    """Test drift detection with both changes."""
    prev = {"mean": 50.0, "std": 10.0}
    current = {"mean": 59.0, "std": 13.0}
    
    assert detect_ruleset_shift(prev, current) is True


def test_compute_metrics_empty():
    """Test metrics computation with empty data."""
    metrics = compute_metrics(
        daily_scores=[],
        life_events=[],
        mapped_count=0,
        total_events=0,
        fallback_count=0,
        ruleset_version="test_v1",
    )
    
    assert metrics.n_days == 0
    assert metrics.daily_score_mean == 50.0
    assert metrics.daily_score_std == 0.0
    assert metrics.positive_event_count == 0
    assert metrics.negative_event_count == 0
    assert metrics.mapped_aspect_ratio == 0.0
    assert metrics.fallback_rate == 0.0


def test_compute_metrics_with_data():
    """Test metrics computation with actual data."""
    daily_scores = [
        DailyScore(
            date=date(2026, 3, 1),
            score=60,
            confidence=0.8,
            top_drivers=[Driver(code="TEST", weight=5.0, implication="Test", matched_aspect="VEN TRI JUP")],
            note="Test",
        ),
        DailyScore(
            date=date(2026, 3, 2),
            score=55,
            confidence=0.75,
            top_drivers=[Driver(code="TEST", weight=3.0, implication="Test", matched_aspect="MOO CON SAT")],
            note="Test",
        ),
        DailyScore(
            date=date(2026, 3, 3),
            score=50,
            confidence=0.7,
            top_drivers=[Driver(code="TEST", weight=2.0, implication="Test", matched_aspect="VEN TRI JUP")],
            note="Test",
        ),
    ]
    
    life_events = [
        MockLifeEvent("Positive"),
        MockLifeEvent("Positive"),
        MockLifeEvent("Negative"),
    ]
    
    metrics = compute_metrics(
        daily_scores=daily_scores,
        life_events=life_events,
        mapped_count=2,
        total_events=3,
        fallback_count=1,
        ruleset_version="test_v1",
    )
    
    assert metrics.n_days == 3
    assert metrics.daily_score_mean == 55.0  # (60+55+50)/3
    assert metrics.daily_score_std > 0
    assert metrics.positive_event_count == 2
    assert metrics.negative_event_count == 1
    assert metrics.mapped_aspect_ratio == 0.667
    assert metrics.fallback_rate == 0.333
    assert len(metrics.top_driver_frequencies) > 0
    assert "VEN TRI JUP" in metrics.top_driver_frequencies
    assert metrics.top_driver_frequencies["VEN TRI JUP"] == 2


def test_compute_metrics_fallback_rate():
    """Test fallback rate calculation."""
    metrics = compute_metrics(
        daily_scores=[],
        life_events=[MockLifeEvent()],
        mapped_count=7,
        total_events=10,
        fallback_count=3,
        ruleset_version="test_v1",
    )
    
    assert metrics.fallback_rate == 0.3


def test_compute_metrics_top_drivers():
    """Test top driver frequency tracking."""
    daily_scores = [
        DailyScore(
            date=date(2026, 3, 1),
            score=60,
            confidence=0.8,
            top_drivers=[
                Driver(code="T1", weight=5.0, implication="Test", matched_aspect="VEN TRI JUP"),
                Driver(code="T2", weight=3.0, implication="Test", matched_aspect="MOO CON SAT"),
            ],
            note="Test",
        ),
        DailyScore(
            date=date(2026, 3, 2),
            score=55,
            confidence=0.75,
            top_drivers=[
                Driver(code="T1", weight=4.0, implication="Test", matched_aspect="VEN TRI JUP"),
                Driver(code="T3", weight=2.0, implication="Test", matched_aspect="SUN SEX MER"),
            ],
            note="Test",
        ),
    ]
    
    metrics = compute_metrics(
        daily_scores=daily_scores,
        life_events=[],
        mapped_count=0,
        total_events=0,
        fallback_count=0,
        ruleset_version="test_v1",
    )
    
    # VEN TRI JUP should appear twice
    assert metrics.top_driver_frequencies.get("VEN TRI JUP") == 2
    assert metrics.top_driver_frequencies.get("MOO CON SAT") == 1
    assert metrics.top_driver_frequencies.get("SUN SEX MER") == 1
