"""Drift detection for ruleset changes."""
from __future__ import annotations

from typing import Dict


def detect_ruleset_shift(
    prev_distribution: Dict[str, float],
    current_distribution: Dict[str, float],
) -> bool:
    """Detect significant shift in score distribution.
    
    Args:
        prev_distribution: Previous run's distribution (mean, std)
        current_distribution: Current run's distribution (mean, std)
    
    Returns:
        True if drift detected, False otherwise
    
    Rules:
        - Mean shift > 8 points triggers drift
        - Std dev change > 20% triggers drift
    """
    prev_mean = prev_distribution.get("mean", 50.0)
    current_mean = current_distribution.get("mean", 50.0)
    mean_shift = abs(current_mean - prev_mean)
    
    prev_std = prev_distribution.get("std", 10.0)
    current_std = current_distribution.get("std", 10.0)
    
    if prev_std > 0:
        std_change_pct = abs(current_std - prev_std) / prev_std
    else:
        std_change_pct = 0.0
    
    return mean_shift > 8.0 or std_change_pct > 0.2
