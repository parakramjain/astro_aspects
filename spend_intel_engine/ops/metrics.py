"""Metrics collection and computation for shopping insights."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

import numpy as np

from spend_intel_engine.domain.models import DailyScore, InsightsMetrics


def compute_metrics(
    daily_scores: List[DailyScore],
    life_events: List[Any],
    mapped_count: int,
    total_events: int,
    fallback_count: int,
    ruleset_version: str,
) -> InsightsMetrics:
    """Compute comprehensive metrics from daily scores and events.
    
    Args:
        daily_scores: List of daily score results
        life_events: List of life event objects
        mapped_count: Number of events that mapped to rules
        total_events: Total number of events processed
        fallback_count: Number of events that used fallback logic
        ruleset_version: Current ruleset version hash
    
    Returns:
        InsightsMetrics object with all computed metrics
    """
    # Calculate ratios from event counters regardless of daily score availability
    mapped_ratio = mapped_count / max(total_events, 1)
    fallback_rate = fallback_count / max(total_events, 1)

    # Count positive vs negative events independent of scoring output
    positive_count = sum(1 for event in life_events if _is_positive_event(event))
    negative_count = len(life_events) - positive_count

    if not daily_scores:
        return InsightsMetrics(
            ruleset_version=ruleset_version,
            n_days=0,
            daily_score_mean=50.0,
            daily_score_std=0.0,
            positive_event_count=positive_count,
            negative_event_count=negative_count,
            mapped_aspect_ratio=round(mapped_ratio, 3),
            fallback_rate=round(fallback_rate, 3),
            top_driver_frequencies={},
        )
    
    scores = [ds.score for ds in daily_scores]
    mean_score = float(np.mean(scores))
    std_score = float(np.std(scores))
    
    # Count positive vs negative events
    positive_count = sum(1 for event in life_events if _is_positive_event(event))
    negative_count = len(life_events) - positive_count
    
    # Collect top driver frequencies
    driver_counter: Counter[str] = Counter()
    for ds in daily_scores:
        for driver in ds.top_drivers:
            if driver.matched_aspect:
                driver_counter[driver.matched_aspect] += 1
    
    top_frequencies = dict(driver_counter.most_common(10))
    
    return InsightsMetrics(
        ruleset_version=ruleset_version,
        n_days=len(daily_scores),
        daily_score_mean=round(mean_score, 2),
        daily_score_std=round(std_score, 2),
        positive_event_count=positive_count,
        negative_event_count=negative_count,
        mapped_aspect_ratio=round(mapped_ratio, 3),
        fallback_rate=round(fallback_rate, 3),
        top_driver_frequencies=top_frequencies,
    )


def _is_positive_event(event: Any) -> bool:
    """Check if event has positive nature."""
    nature = str(getattr(event, "aspectNature", "Neutral")).lower()
    return nature == "positive"
