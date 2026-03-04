from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


def _default_csv_path(filename: str) -> str:
    return str(_default_data_dir() / filename)


@dataclass(frozen=True)
class BirthPayload:
    name: str
    dateOfBirth: str
    timeOfBirth: str
    placeOfBirth: str
    timeZone: str
    latitude: float
    longitude: float
    lang_code: str = "en"


@dataclass(frozen=True)
class Driver:
    code: str
    weight: float
    implication: str
    matched_aspect: Optional[str] = None


@dataclass(frozen=True)
class SpendProfile:
    score: int
    category: str
    description: str
    top_drivers: List[Driver] = field(default_factory=list)


@dataclass(frozen=True)
class DailyScore:
    date: date
    score: int
    confidence: float
    top_drivers: List[Driver] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class InsightsMetrics:
    ruleset_version: str
    n_days: int
    daily_score_mean: float
    daily_score_std: float
    positive_event_count: int
    negative_event_count: int
    mapped_aspect_ratio: float
    fallback_rate: float
    top_driver_frequencies: Dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ShoppingInsights:
    spend_profile: SpendProfile
    daily_scores: List[DailyScore]
    ruleset_version: str
    run_id: str
    metrics: Optional[InsightsMetrics] = None


@dataclass(frozen=True)
class ShoppingCfg:
    natal_spend_aspects_csv: str = field(default_factory=lambda: _default_csv_path("natal_spend_aspects.csv"))
    transit_daily_shopping_aspects_csv: str = field(default_factory=lambda: _default_csv_path("transit_daily_shopping_aspects.csv"))
    natal_structure_signals_csv: str = field(default_factory=lambda: _default_csv_path("natal_structure_signals.csv"))
    moon_spending_aspects_csv: str = field(default_factory=lambda: _default_csv_path("moon_spending_aspects.csv"))
    purchase_type: str = "big_ticket"  # Literal["essentials", "big_ticket", "luxury"]
    base_score: float = 50.0
    spend_scale: float = 22.0
    daily_base_score: float = 50.0
    major_event_weight: float = 1.0
    minor_event_weight: float = 0.6
    major_amplitude: float = 12.0
    minor_amplitude: float = 7.0
    moon_trigger_enabled: bool = True
    moon_trigger_amplitude: float = 4.0
    moon_phase_by_date: Optional[Dict[str, str]] = None
    top_driver_limit: int = 5
    profile_driver_phrase_limit: int = 3
    logger_name: str = "shopping_score"
    structure_feature_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "VENUS_CONDITION": 2.0,
            "SATURN_PROMINENCE": 2.5,
            "JUPITER_PROMINENCE": 2.5,
            "SECOND_RULER_STABILITY": 1.8,
            "EIGHTH_RULER_PRESSURE": 1.8,
        }
    )
    aspect_type_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "CON": 1.0,
            "TRI": 0.85,
            "SEX": 0.7,
            "SQR": 0.9,
            "OPP": 1.0,
        }
    )
    event_type_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "MAJOR": 1.0,
            "MINOR": 0.6,
        }
    )


@dataclass(frozen=True)
class RuleMaps:
    natal_spend_implications: Dict[str, str]
    transit_daily_implications: Dict[str, str]
    natal_structure_implications: Dict[str, str]
    moon_spending_implications: Dict[str, str]
    ruleset_version: str


@dataclass(frozen=True)
class NatalStructureSignals:
    values: Dict[str, float]
    implications: Dict[str, str]


@dataclass(frozen=True)
class ScoringContext:
    run_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
