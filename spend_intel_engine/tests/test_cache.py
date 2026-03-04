"""Unit tests for caching utilities."""
from __future__ import annotations

import pytest

from spend_intel_engine.utils.cache import compute_chart_hash, compute_user_hash


def test_compute_chart_hash():
    """Test chart hash computation."""
    hash1 = compute_chart_hash("1990-01-01", "10:30", "New York", 40.7128, -74.0060)
    hash2 = compute_chart_hash("1990-01-01", "10:30", "New York", 40.7128, -74.0060)
    hash3 = compute_chart_hash("1990-01-02", "10:30", "New York", 40.7128, -74.0060)
    
    # Same inputs should produce same hash
    assert hash1 == hash2
    
    # Different inputs should produce different hash
    assert hash1 != hash3
    
    # Hash should be 16 characters
    assert len(hash1) == 16


def test_compute_user_hash():
    """Test user hash computation for logging."""
    hash1 = compute_user_hash("1990-01-01", "10:30", "New York")
    hash2 = compute_user_hash("1990-01-01", "10:30", "New York")
    hash3 = compute_user_hash("1990-01-02", "10:30", "New York")
    
    # Same inputs should produce same hash
    assert hash1 == hash2
    
    # Different inputs should produce different hash
    assert hash1 != hash3
    
    # Hash should be 12 characters (truncated)
    assert len(hash1) == 12


def test_chart_hash_sensitivity():
    """Test that chart hash is sensitive to coordinate changes."""
    base_hash = compute_chart_hash("1990-01-01", "10:30", "NYC", 40.7128, -74.0060)
    
    # Small latitude change
    lat_hash = compute_chart_hash("1990-01-01", "10:30", "NYC", 40.7129, -74.0060)
    assert base_hash != lat_hash
    
    # Small longitude change
    lon_hash = compute_chart_hash("1990-01-01", "10:30", "NYC", 40.7128, -74.0061)
    assert base_hash != lon_hash
    
    # Time change
    time_hash = compute_chart_hash("1990-01-01", "10:31", "NYC", 40.7128, -74.0060)
    assert base_hash != time_hash
