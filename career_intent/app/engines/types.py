from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class DailyScore:
    date: str
    opportunity_raw: float
    risk_raw: float
    opportunity_score: int
    risk_score: int
    drivers: List[str] = field(default_factory=list)
    positive_drivers: List[str] = field(default_factory=list)
    negative_drivers: List[str] = field(default_factory=list)
    evidence: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WindowResult:
    start_date: str
    end_date: str
    score: int
    top_drivers: List[str]
    quality: int = 0
    drivers_detail: List[Dict[str, object]] = field(default_factory=list)
    is_neutral: bool = False


@dataclass(frozen=True)
class FeatureSummary:
    positive_count: int
    negative_count: int
    neutral_count: int
    confidence: float
    driver_counts: Dict[str, int]
    drivers_coverage: float = 0.0
    data_quality_flags: List[str] = field(default_factory=list)
    dimension_signals: Dict[str, float] = field(default_factory=dict)
