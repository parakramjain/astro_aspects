"""Caching utilities for performance optimization."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any, Dict, Optional


def compute_chart_hash(
    dob: str,
    tob: str,
    place: str,
    latitude: float,
    longitude: float,
) -> str:
    """Compute deterministic hash of birth chart parameters."""
    key = f"{dob}|{tob}|{place}|{latitude:.6f}|{longitude:.6f}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@lru_cache(maxsize=128)
def cached_natal_structure_features(
    chart_hash: str,
    ruleset_version: str,
    feature_data: str,  # JSON string of feature values
) -> Dict[str, float]:
    """Cache natal structure feature computation.
    
    Args:
        chart_hash: Hash identifying unique birth chart
        ruleset_version: Version of ruleset being used
        feature_data: Serialized feature data (for cache invalidation)
    
    Returns:
        Dictionary of feature values
    """
    import json
    return json.loads(feature_data)


def compute_user_hash(dob: str, tob: str, place: str) -> str:
    """Compute anonymized user hash for logging (without PII)."""
    key = f"{dob}|{tob}|{place}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
